#include <jni.h>
#include <string>
#include <android/log.h>
#include "libusb.h"
#include "libuvc/libuvc.h"
#include <unistd.h>
#include <thread>
#include <atomic>

#define ALOGD(...) __android_log_print(ANDROID_LOG_DEBUG, "TactileNavNative", __VA_ARGS__)
#define ALOGE(...) __android_log_print(ANDROID_LOG_ERROR, "TactileNavNative", __VA_ARGS__)

std::atomic<bool> is_streaming(false);

JavaVM* g_jvm = nullptr;
jobject g_main_activity = nullptr;
jmethodID g_receive_frame_method = nullptr;

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {
    g_jvm = vm;
    return JNI_VERSION_1_6;
}

struct uvc_device_handle {
    struct uvc_device *dev;
    struct uvc_device_handle *prev, *next;
    struct libusb_device_handle *usb_devh;
    struct uvc_device_info *info;
    struct libusb_transfer *status_xfer;
    uint8_t status_buf[32];
    uvc_status_callback_t *status_cb;
    void *status_user_ptr;
    uvc_button_callback_t *button_cb;
    void *button_user_ptr;
    struct uvc_stream_handle *streams;
    uint8_t is_isight;
};

void frame_callback(uvc_frame_t *frame, void *ptr) {
    if (g_jvm == nullptr || g_main_activity == nullptr || g_receive_frame_method == nullptr) return;

    JNIEnv *env;
    bool attached = false;

    int getEnvStat = g_jvm->GetEnv((void **)&env, JNI_VERSION_1_6);
    if (getEnvStat == JNI_EDETACHED) {
        if (g_jvm->AttachCurrentThread(&env, NULL) != 0) return;
        attached = true;
    }

    jbyteArray j_bytes = env->NewByteArray(frame->data_bytes);
    env->SetByteArrayRegion(j_bytes, 0, frame->data_bytes, (jbyte*)frame->data);

    env->CallVoidMethod(g_main_activity, g_receive_frame_method, j_bytes);

    env->DeleteLocalRef(j_bytes);
    if (attached) g_jvm->DetachCurrentThread();
}

extern "C"
JNIEXPORT void JNICALL
Java_com_example_tactilenavigator_MainActivity_passFileDescriptorToNative(
        JNIEnv *env,
        jobject thiz,
        jint fd) {

    if (g_main_activity == nullptr) {
        g_main_activity = env->NewGlobalRef(thiz);
        jclass clazz = env->GetObjectClass(g_main_activity);
        g_receive_frame_method = env->GetMethodID(clazz, "onFrameReceived", "([B)V");
    }
    ALOGD("C++ received File Descriptor: %d. Booting hardware...", fd);

    libusb_set_option(NULL, LIBUSB_OPTION_NO_DEVICE_DISCOVERY, NULL);

    int init_res = libusb_init(NULL);
    if (init_res < 0) {
        ALOGE("libusb_init failed: %d", init_res);
        return;
    }

    libusb_set_option(NULL, LIBUSB_OPTION_LOG_LEVEL, LIBUSB_LOG_LEVEL_DEBUG);

    libusb_device_handle *usb_handle = nullptr;
    int wrap_res = libusb_wrap_sys_device(NULL, (intptr_t)fd, &usb_handle);
    if (wrap_res < 0 || usb_handle == nullptr) {
        ALOGE("Failed to wrap file descriptor! Error: %d", wrap_res);
        libusb_exit(NULL);
        return;
    }

    libusb_device *usb_dev = libusb_get_device(usb_handle);
    libusb_device_descriptor desc;
    libusb_get_device_descriptor(usb_dev, &desc);
    ALOGD("HARDWARE LOCK ACHIEVED! Camera VID: %04x, PID: %04x", desc.idVendor, desc.idProduct);

    uvc_context_t *uvc_ctx;
    uvc_error_t uvc_res = uvc_init(&uvc_ctx, NULL);
    if (uvc_res < 0) {
        ALOGE("uvc_init failed: %d", uvc_res);
        return;
    }
    ALOGD("libuvc initialized successfully.");

    // ------------------------------------------------------------------
    // STEP 6: PROBE THE CAMERA HARDWARE (THE CLEAN WAY)
    // ------------------------------------------------------------------

    uvc_device_handle_t *devh = nullptr;
    uvc_res = uvc_wrap_fd(uvc_ctx, usb_handle, &devh);

    if (uvc_res < 0) {
        ALOGE("uvc_wrap_fd failed: %d", uvc_res);
        return;
    }
    ALOGD("Successfully wrapped Android FD into libuvc!");

    uvc_stream_ctrl_t ctrl;
    uvc_res = uvc_get_stream_ctrl_format_size(
            devh, &ctrl,
            UVC_FRAME_FORMAT_MJPEG,
            640, 240,
            30
    );

    if (uvc_res < 0) {
        ALOGE("Failed to negotiate stream control: %d.", uvc_res);
        return;
    }
    ALOGD("Stream negotiation successful!");

    if (libusb_kernel_driver_active(usb_handle, 0) == 1) {
        ALOGD("Android kernel is locking Interface 0. Forcing detach...");
        libusb_detach_kernel_driver(usb_handle, 0);
    }

    if (libusb_kernel_driver_active(usb_handle, 1) == 1) {
        ALOGD("Android kernel is locking Interface 1. Forcing detach...");
        libusb_detach_kernel_driver(usb_handle, 1);
    }

    int claim_ctrl = libusb_claim_interface(usb_handle, 0);
    if (claim_ctrl < 0) {
        ALOGE("Failed to claim Interface 0 (VideoControl). Error: %d", claim_ctrl);
    } else {
        ALOGD("Successfully claimed Interface 0 (VideoControl)!");
    }

    int claim_stream = libusb_claim_interface(usb_handle, 1);
    if (claim_stream < 0) {
        ALOGE("Failed to claim Interface 1 (VideoStreaming). Error: %d", claim_stream);
    } else {
        ALOGD("Successfully claimed Interface 1 (VideoStreaming)!");
    }


    uvc_res = uvc_start_streaming(devh, &ctrl, frame_callback, nullptr, 0);
    if (uvc_res < 0) {
        ALOGE("uvc_start_streaming failed: %d", uvc_res);
        return;
    }

    is_streaming = true;
    std::thread usb_poll_thread([]() {
        ALOGD("BACKGROUND THREAD: USB Event Poller started! Cranking the pump...");
        int tick = 0;
        while (is_streaming) {
            struct timeval tv = {0, 100000};
            libusb_handle_events_timeout_completed(NULL, &tv, NULL);

            if (++tick % 30 == 0) {
                ALOGD("Pump is spinning... waiting for Android kernel to route video packets...");
            }
        }
        ALOGD("BACKGROUND THREAD: USB Event Poller stopped.");
    });

    usb_poll_thread.detach();

    ALOGD("STREAM STARTED! Check Logcat for frame callback messages.");
}
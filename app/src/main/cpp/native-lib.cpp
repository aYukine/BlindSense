#include <jni.h>
#include <string>
#include <android/log.h>

#define LOG_TAG "TactileNavNative"
#define ALOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)
#define ALOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

extern "C"
JNIEXPORT void JNICALL
Java_com_example_tactilenavigator_MainActivity_passFileDescriptorToNative(
        JNIEnv *env,
        jobject thiz,
        jint fd) {

    if (fd < 0) {
        ALOGE("Received invalid File Descriptor: %d", fd);
        return;
    }

    ALOGD("SUCCESS! C++ successfully received File Descriptor: %d", fd);

}
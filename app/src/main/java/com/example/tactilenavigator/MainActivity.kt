package com.example.tactilenavigator

import android.content.Context
import android.content.Intent
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.IntentFilter
import android.widget.Button
import android.Manifest
import android.content.pm.PackageManager
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import android.graphics.BitmapFactory
import android.widget.ImageView

class MainActivity : AppCompatActivity() {

    private lateinit var usbManager: UsbManager
    private var keepAliveConnection: android.hardware.usb.UsbDeviceConnection? = null

    private val TAG = "TactileNav"
    private val ACTION_USB_PERMISSION = "com.example.tactilenavigator.USB_PERMISSION"

    private val CAMERA_PERMISSION_CODE = 100

    init {
        System.loadLibrary("tactilenavigator")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        usbManager = getSystemService(Context.USB_SERVICE) as UsbManager

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            Log.d(TAG, "Requesting standard Camera runtime permission...")
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), CAMERA_PERMISSION_CODE)
        }

        val filter = IntentFilter(ACTION_USB_PERMISSION)
        registerReceiver(usbReceiver, filter, RECEIVER_EXPORTED)

        findViewById<Button>(R.id.btnConnect).setOnClickListener {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                Log.d(TAG, "Button tapped! Searching for camera...")
                findAndRequestUsbCamera()
            } else {
                Log.e(TAG, "Cannot access USB. The app needs standard Camera permissions first!")
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), CAMERA_PERMISSION_CODE)
            }
        }
    }

    private fun findAndRequestUsbCamera() {
        val deviceList = usbManager.deviceList
        if (deviceList.isEmpty()) {
            Log.e(TAG, "No USB devices plugged in!")
            return
        }

        val cameraDevice = deviceList.values.first()
        Log.d(TAG, "Found ${cameraDevice.deviceName}. Requesting permission natively...")

        val intent = Intent(ACTION_USB_PERMISSION).apply { setPackage(packageName) }
        val permissionIntent = PendingIntent.getBroadcast(
            this, 0, intent,
            PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        usbManager.requestPermission(cameraDevice, permissionIntent)
    }

    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (ACTION_USB_PERMISSION == intent.action) {
                synchronized(this) {
                    val device: UsbDevice? = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE)

                    if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                        Log.d(TAG, "USER TAPPED ALLOW! Permission granted.")
                        device?.let { openUsbDevice(it) }
                    } else {
                        Log.e(TAG, "Permission denied by user or OS.")
                    }
                }
            }
        }
    }

    private fun openUsbDevice(device: UsbDevice) {
        val connection = usbManager.openDevice(device)
        if (connection != null) {
            keepAliveConnection = connection

            for (i in 0 until device.interfaceCount) {
                val usbInterface = device.getInterface(i)
                val claimed = connection.claimInterface(usbInterface, true)
                Log.d(TAG, "Claimed Interface $i in Kotlin: $claimed")
            }

            val fileDescriptor = connection.fileDescriptor
            Log.d(TAG, "Device opened successfully. File Descriptor: $fileDescriptor")

            passFileDescriptorToNative(fileDescriptor)
        } else {
            Log.e(TAG, "Failed to open USB connection. Connection object is null.")
        }
    }

    fun onFrameReceived(jpegBytes: ByteArray) {
        val bitmap = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)

        if (bitmap != null) {
            runOnUiThread {
                findViewById<ImageView>(R.id.cameraPreview).setImageBitmap(bitmap)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiver(usbReceiver)
    }

    external fun passFileDescriptorToNative(fd: Int)
}
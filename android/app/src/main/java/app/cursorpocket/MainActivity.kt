package app.cursorpocket

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.atomic.AtomicInteger

class MainActivity : AppCompatActivity() {
    private lateinit var web: WebView
    private lateinit var setup: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        ensureChannel()
        web = findViewById(R.id.web)
        setup = findViewById(R.id.setup)
        configureWebView()
        findViewById<Button>(R.id.connect).setOnClickListener {
            askNotifyPermission()
            saveAndLoad()
        }
        val saved = prefs().getString(KEY_URL, "").orEmpty()
        if (saved.isBlank()) {
            showSetup()
        } else {
            askNotifyPermission()
            load(saved)
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_change_url) {
            showSetup(prefill = prefs().getString(KEY_URL, ""))
            return true
        }
        return super.onOptionsItemSelected(item)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.visibility == View.VISIBLE && web.canGoBack()) {
            web.goBack()
        } else {
            super.onBackPressed()
        }
    }

    private fun saveAndLoad() {
        val raw = findViewById<EditText>(R.id.url).text.toString().trim()
        val url = normalize(raw)
        if (url == null) {
            Toast.makeText(this, R.string.bad_url, Toast.LENGTH_LONG).show()
            return
        }
        prefs().edit().putString(KEY_URL, url).apply()
        load(url)
    }

    private fun showSetup(prefill: String? = null) {
        setup.visibility = View.VISIBLE
        web.visibility = View.GONE
        val field = findViewById<EditText>(R.id.url)
        if (!prefill.isNullOrBlank()) field.setText(prefill)
    }

    override fun onResume() {
        super.onResume()
        if (this::web.isInitialized) {
            // LAN / two VMs still work when Android reports "no internet".
            web.setNetworkAvailable(true)
        }
    }

    private fun laptopUrl(): String = prefs().getString(KEY_URL, "").orEmpty().trimEnd('/')

    private fun load(url: String) {
        setup.visibility = View.GONE
        web.visibility = View.VISIBLE
        web.setNetworkAvailable(true)
        Thread {
            try {
                val html = httpGet(url).decodeToString()
                val base = url.trimEnd('/') + "/"
                runOnUiThread {
                    web.loadDataWithBaseURL(base, html, "text/html", "utf-8", url)
                }
            } catch (e: Exception) {
                runOnUiThread { web.loadUrl(url) }
            }
        }.start()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.cacheMode = WebSettings.LOAD_NO_CACHE
        web.settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        web.settings.blockNetworkImage = false
        web.settings.blockNetworkLoads = false
        web.setNetworkAvailable(true)
        web.webViewClient =
            object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView,
                    request: WebResourceRequest,
                ): WebResourceResponse? {
                    if (request.method != "GET") return null
                    val uri = request.url ?: return null
                    if (!isLaptop(uri)) return null
                    val path = uri.path ?: ""
                    if (path.contains("/events")) return null
                    return try {
                        proxyGet(uri.toString())
                    } catch (_: Exception) {
                        null
                    }
                }

                override fun onReceivedError(
                    view: WebView,
                    request: WebResourceRequest,
                    error: WebResourceError,
                ) {
                    if (!request.isForMainFrame) return
                    val description = error.description ?: "unknown error"
                    val target = request.url?.toString() ?: ""
                    view.loadData(
                        """
                        <html><body style="background:#000;color:#f5f5f7;font-family:-apple-system,sans-serif;padding:28px">
                        <h2>Cannot reach the laptop</h2>
                        <p>$description</p>
                        <p style="color:#8e8e93">$target</p>
                        <p>Internet is not required. Same Wi-Fi, two VMs, or USB.</p>
                        <p>Android emulator / nested VM: <code>http://10.0.2.2:8787</code></p>
                        <p>USB: <code>adb reverse tcp:8787 tcp:8787</code> then <code>http://127.0.0.1:8787</code></p>
                        </body></html>
                        """.trimIndent(),
                        "text/html",
                        "utf-8",
                    )
                }
            }
        web.webChromeClient = WebChromeClient()
        web.addJavascriptInterface(PocketBridge(this), "PocketNative")
    }

    private fun isLaptop(uri: Uri): Boolean {
        val saved = laptopUrl()
        if (saved.isBlank()) return false
        val laptop = Uri.parse(saved)
        if (!uri.host.equals(laptop.host, ignoreCase = true)) return false
        return effectivePort(uri) == effectivePort(laptop)
    }

    private fun ensureChannel() {
        val mgr = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(CHANNEL, "Cursor Pocket", NotificationManager.IMPORTANCE_HIGH)
        channel.description = "When Cursor or a Cloud Agent finishes on the laptop"
        channel.enableVibration(true)
        channel.enableLights(true)
        mgr.createNotificationChannel(channel)
    }

    private fun askNotifyPermission() {
        if (Build.VERSION.SDK_INT >= 33) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 12)
            }
        }
    }

    private fun prefs() = getSharedPreferences("pocket", Context.MODE_PRIVATE)

    class PocketBridge(private val app: MainActivity) {
        private val main = Handler(Looper.getMainLooper())

        @JavascriptInterface
        fun notifyDone(title: String, body: String) {
            main.post { post(title, body) }
        }

        @JavascriptInterface
        fun notificationsReady(): Boolean = true

        @JavascriptInterface
        fun http(method: String, path: String, body: String, token: String): String {
            return try {
                val base = app.laptopUrl()
                if (base.isBlank()) {
                    return JSONObject().put("status", 0).put("error", "No laptop URL").toString()
                }
                val url =
                    if (path.startsWith("http://") || path.startsWith("https://")) {
                        path
                    } else {
                        base + if (path.startsWith("/")) path else "/$path"
                    }
                javaHttp(method, url, body, token)
            } catch (e: Exception) {
                JSONObject()
                    .put("status", 0)
                    .put("error", e.message ?: "Cannot reach the laptop")
                    .toString()
            }
        }

        private fun post(title: String, body: String) {
            val launch = Intent(app, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val pending = PendingIntent.getActivity(
                app,
                0,
                launch,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            val mgr = app.getSystemService(NotificationManager::class.java)
            val note = NotificationCompat.Builder(app, CHANNEL)
                .setSmallIcon(R.drawable.ic_stat_notify)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setDefaults(NotificationCompat.DEFAULT_ALL)
                .setContentIntent(pending)
                .build()
            mgr.notify(NEXT_ID.incrementAndGet(), note)
        }
    }

    companion object {
        private const val KEY_URL = "laptop_url"
        private const val CHANNEL = "cursor_pocket"
        private val NEXT_ID = AtomicInteger(100)

        fun normalize(raw: String): String? {
            val trimmed = raw.trim()
            if (trimmed.isEmpty()) return null
            val withScheme =
                if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
                    trimmed
                } else {
                    "http://$trimmed"
                }
            return withScheme.trimEnd('/')
        }

        fun effectivePort(uri: Uri): Int {
            if (uri.port != -1) return uri.port
            return if (uri.scheme.equals("https", ignoreCase = true)) 443 else 80
        }

        fun httpGet(url: String): ByteArray {
            val conn = open(url, "GET", null, "")
            val code = conn.responseCode
            val stream = if (code in 200..399) conn.inputStream else conn.errorStream
            val bytes = stream?.readBytes() ?: ByteArray(0)
            conn.disconnect()
            if (code !in 200..399) {
                throw IllegalStateException("HTTP $code")
            }
            return bytes
        }

        fun proxyGet(url: String): WebResourceResponse {
            val conn = open(url, "GET", null, "")
            val code = conn.responseCode
            val rawType = conn.contentType ?: "application/octet-stream"
            val mime = rawType.split(";", limit = 2)[0].trim().ifBlank { "application/octet-stream" }
            val stream =
                (if (code in 200..399) conn.inputStream else conn.errorStream)
                    ?: ByteArrayInputStream(ByteArray(0))
            val headers =
                conn.headerFields
                    .filterKeys { it != null }
                    .mapValues { it.value.joinToString(",") }
            return WebResourceResponse(mime, "utf-8", code, "OK", headers, stream)
        }

        fun javaHttp(method: String, url: String, body: String, token: String): String {
            val conn = open(url, method.uppercase(), body, token)
            val code = conn.responseCode
            val stream = if (code in 200..399) conn.inputStream else conn.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.readText() ?: ""
            conn.disconnect()
            return JSONObject()
                .put("status", code)
                .put("body", text)
                .toString()
        }

        private fun open(url: String, method: String, body: String?, token: String): HttpURLConnection {
            val conn = URL(url).openConnection() as HttpURLConnection
            conn.connectTimeout = 8000
            conn.readTimeout = 25000
            conn.instanceFollowRedirects = true
            conn.requestMethod = method
            conn.useCaches = false
            if (token.isNotBlank()) {
                conn.setRequestProperty("Authorization", "Bearer $token")
            }
            if (method != "GET" && method != "HEAD") {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                val payload = (body ?: "").toByteArray(Charsets.UTF_8)
                conn.setRequestProperty("Content-Length", payload.size.toString())
                conn.outputStream.use { it.write(payload) }
            }
            return conn
        }
    }
}

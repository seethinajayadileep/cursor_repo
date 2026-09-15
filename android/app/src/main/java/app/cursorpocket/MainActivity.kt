package app.cursorpocket

import android.annotation.SuppressLint
import android.content.Context
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    private lateinit var web: WebView
    private lateinit var setup: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        web = findViewById(R.id.web)
        setup = findViewById(R.id.setup)
        configureWebView()
        findViewById<Button>(R.id.connect).setOnClickListener { saveAndLoad() }
        val saved = prefs().getString(KEY_URL, "").orEmpty()
        if (saved.isBlank()) {
            showSetup()
        } else {
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

    private fun load(url: String) {
        setup.visibility = View.GONE
        web.visibility = View.VISIBLE
        web.loadUrl(url)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.cacheMode = WebSettings.LOAD_DEFAULT
        web.settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        web.webViewClient = WebViewClient()
        web.webChromeClient = WebChromeClient()
    }

    private fun prefs() = getSharedPreferences("pocket", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_URL = "laptop_url"

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
    }
}

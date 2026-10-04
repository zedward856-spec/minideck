package com.zedward.minideck;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebSettings;
import android.webkit.WebView;

/** Full-screen WebView over the bundled minideck site (assets/www), served from a fake https origin. */
public class MainActivity extends Activity {
    private WebView web;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        WebView.setWebContentsDebuggingEnabled(true);    // chrome://inspect from the PC
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);             // same black as the loading video
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);  // the logo video on the deck's screen
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);      // assets are local, never stale
        if (android.os.Build.VERSION.SDK_INT >= 33) s.setAlgorithmicDarkeningAllowed(false);  // the site is already dark

        web.setWebViewClient(new AssetClient(this));
        setContentView(web);

        if (saved != null) web.restoreState(saved);
        else web.loadUrl(AssetClient.ORIGIN + "index.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override public void onResume() { super.onResume(); web.onResume(); }
    @Override public void onPause() { web.onPause(); super.onPause(); }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();   // in-page #section jumps
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }
}

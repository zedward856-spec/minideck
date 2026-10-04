package com.zedward.minideck;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * Serves assets/www under https://appassets.androidplatform.net/ so ES modules, fetch() and the
 * importmap behave exactly like the hosted site. Any other link (mailto:, web) goes to the system.
 */
public class AssetClient extends WebViewClient {
    static final String HOST = "appassets.androidplatform.net";
    static final String ORIGIN = "https://" + HOST + "/";

    private final Activity act;

    AssetClient(Activity act) { this.act = act; }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
        Uri u = req.getUrl();
        if (!HOST.equals(u.getHost())) return blocked();   // offline app: nothing leaves the phone
        String path = u.getPath();
        if (path == null || path.equals("/")) path = "/index.html";
        try {
            InputStream in = act.getAssets().open("www" + path);
            Map<String, String> h = new HashMap<>();
            h.put("Access-Control-Allow-Origin", "*");
            h.put("Cache-Control", "no-cache");
            return new WebResourceResponse(mime(path), mime(path).startsWith("text/") ? "utf-8" : null,
                    200, "OK", h, in);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found", null, null);
        }
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
        Uri u = req.getUrl();
        if (HOST.equals(u.getHost())) return false;
        try {
            act.startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (Exception ignored) { }
        return true;
    }

    private static WebResourceResponse blocked() {
        return new WebResourceResponse("text/plain", "utf-8", 403, "Offline", null, null);
    }

    private static final Map<String, String> TYPES = new HashMap<>();
    static {
        TYPES.put("html", "text/html");
        TYPES.put("css", "text/css");
        TYPES.put("js", "text/javascript");
        TYPES.put("json", "application/json");
        TYPES.put("glb", "model/gltf-binary");
        TYPES.put("png", "image/png");
        TYPES.put("svg", "image/svg+xml");
        TYPES.put("mp4", "video/mp4");
        TYPES.put("woff2", "font/woff2");
    }

    static String mime(String path) {
        int dot = path.lastIndexOf('.');
        String t = dot < 0 ? null : TYPES.get(path.substring(dot + 1).toLowerCase());
        return t != null ? t : "application/octet-stream";
    }
}

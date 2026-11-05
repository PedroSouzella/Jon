package com.joaovitor.joncar.uno;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.view.WindowManager;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * JON OS — Launcher Automotivo Nativo para Central Multimídia MP10 9" (Fiat Uno 2006)
 * - Detecta tanto Partida Fria (Boot) quanto Pós-Chave ACC (Standby/Wakeup da multimídia)
 * - Ao desligar a chave (onPause): corta o som do rádio/música imediatamente
 * - Ao ligar a chave (onResume): dispara a saudação estilo JARVIS para o João Vitor
 */
public class MainActivity extends Activity {
    private WebView webView;
    private boolean carroEstavaDesligado = false;

    public class PonteAutomotiva {
        @JavascriptInterface
        public void abrirBluetooth() {
            try {
                Intent i = new Intent(Settings.ACTION_BLUETOOTH_SETTINGS);
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
            } catch (Exception ignored) {}
        }

        @JavascriptInterface
        public void abrirConfiguracoes() {
            try {
                Intent i = new Intent(Settings.ACTION_SETTINGS);
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
            } catch (Exception ignored) {}
        }

        @JavascriptInterface
        public void irParaMenuOriginal() {
            moveTaskToBack(true);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        ativarTelaCheiaImersiva();

        webView = new WebView(this);
        setContentView(webView);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setGeolocationEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);

        webView.addJavascriptInterface(new PonteAutomotiva(), "AndroidUno");
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(() -> request.grant(request.getResources()));
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }
        });

        webView.loadUrl("file:///android_asset/carro.html");
    }

    @Override
    protected void onPause() {
        super.onPause();
        // Quando você desliga a chave do Uno (ACC OFF), a multimídia entra em standby:
        // pausamos o rádio e marcamos que o carro foi desligado.
        carroEstavaDesligado = true;
        if (webView != null) {
            webView.evaluateJavascript("if(window.aoDesligarChaveUno) window.aoDesligarChaveUno();", null);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        ativarTelaCheiaImersiva();
        // Quando você gira a chave do Uno novamente (ACC ON), a multimídia acorda:
        // o Jon dá as boas-vindas ao João Vitor automaticamente!
        if (carroEstavaDesligado && webView != null) {
            carroEstavaDesligado = false;
            webView.evaluateJavascript("if(window.aoLigarChaveUno) window.aoLigarChaveUno();", null);
        }
    }

    private void ativarTelaCheiaImersiva() {
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) ativarTelaCheiaImersiva();
    }

    @Override
    public void onBackPressed() {
        // Evita fechar o Launcher do carro por engano
    }
}

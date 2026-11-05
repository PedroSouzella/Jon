# -*- coding: utf-8 -*-
"""
Gerador automático do APK nativo: JonUno9p.apk
Baixa as ferramentas portáteis oficiais (OpenJDK + Android Build Tools) se não existirem
e compila o aplicativo Android pronto para colocar no Pendrive e instalar na multimídia 9" do Uno.
"""
import os
import shutil
import subprocess
import urllib.request
import zipfile

PASTA_ANDROID = os.path.dirname(os.path.abspath(__file__))
PASTA_JON = os.path.dirname(PASTA_ANDROID)
CACHE_SDK = os.path.join(PASTA_ANDROID, ".sdk_portable")
BUILD_DIR = os.path.join(PASTA_ANDROID, "build_out")

URL_JDK = "https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip"
URL_BUILD_TOOLS = "https://dl.google.com/android/repository/build-tools_r33.0.2-windows.zip"
URL_PLATFORM = "https://dl.google.com/android/repository/platform-33_r02.zip"


def atualizar_html_ponte():
    import base64
    caminho_html = os.path.join(PASTA_JON, "web", "carro.html")
    with open(caminho_html, "r", encoding="utf-8") as f:
        h = f.read()

    if "btn-desligar-jon" not in h:
        mp3_off = os.path.join(PASTA_JON, "web", "desligando.mp3")
        b3 = "data:audio/mpeg;base64," + base64.b64encode(open(mp3_off, "rb").read()).decode() if os.path.exists(mp3_off) else ""
        btn_off = '<button class="btn-mini" id="btn-desligar-jon" style="border-color:var(--vermelho);color:var(--vermelho)" title="Desligar / Standby">⏻ DESLIGAR</button>\n      '
        h = h.replace('<button class="btn-mini" id="btn-bt-nativo"', btn_off + '<button class="btn-mini" id="btn-bt-nativo"', 1)
        tela_off = '<div id="standby-screen" style="position:fixed;inset:0;z-index:9500;background:#000;display:none;flex-direction:column;align-items:center;justify-content:center;cursor:pointer"><div style="font:700 12px monospace;color:#2b1f4f;letter-spacing:0.3em">◆ JON OS EM STANDBY • TOQUE NA TELA PARA LIGAR O UNO</div></div>\n'
        h = h.replace('<div id="boot-screen">', tela_off + '<div id="boot-screen">', 1)
        js_off = (
            f'const AUDIO_DESLIGANDO = "{b3}";\n'
            'function desligarMultimidiaUno() {\n'
            '  if (radioTocando) { playerRadio.pause(); radioTocando = false; atualizarVisorRadio(); }\n'
            '  if (emMarchaRe) ativarCameraRe(false);\n'
            '  falarJarvis("Desligando os sistemas do Uno. Até a próxima, João Vitor.", () => {\n'
            '    document.querySelector("#standby-screen").style.display = "flex";\n'
            '  }, AUDIO_DESLIGANDO);\n'
            '}\n'
            'document.querySelector("#btn-desligar-jon").addEventListener("click", desligarMultimidiaUno);\n'
            'document.querySelector("#standby-screen").addEventListener("click", () => {\n'
            '  document.querySelector("#standby-screen").style.display = "none";\n'
            '  window.aoLigarChaveUno();\n'
            '});\n'
        )
        h = h.replace("window.aoDesligarChaveUno = function() {", js_off + "window.aoDesligarChaveUno = function() {", 1)
        cmd_off = 'if (/\\b(desligar|desliga o carro|ate mais|ate logo|modo standby|dormir)\\b/.test(norm)) { desligarMultimidiaUno(); return; }\n  '
        h = h.replace("if (/\\b(camera de re|", cmd_off + "if (/\\b(camera de re|", 1)
        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(h)

    if "btn-bt-nativo" not in h:
        alvo1 = '<button class="btn-mini" id="btn-tela-cheia" title="Tela Cheia Nativa">⛶ TELA CHEIA</button>'
        novo1 = (
            '<button class="btn-mini" id="btn-bt-nativo" title="Abrir Bluetooth da Multimídia">📱 BLUETOOTH</button>\n'
            '      <button class="btn-mini" id="btn-menu-original" title="Alternar para o menu original da Multimídia">⚙️ MULTIMÍDIA</button>\n'
            '      ' + alvo1
        )
        alvo2 = '$("#btn-tela-cheia").addEventListener("click", () => {'
        novo2 = (
            '$("#btn-bt-nativo").addEventListener("click", () => {\n'
            '  if (window.AndroidUno) window.AndroidUno.abrirBluetooth();\n'
            '  else falarJarvis("No carro, este botão abre a tela de Bluetooth nativa da sua multimídia.");\n'
            '});\n'
            '$("#btn-menu-original").addEventListener("click", () => {\n'
            '  if (window.AndroidUno) window.AndroidUno.irParaMenuOriginal();\n'
            '  else falarJarvis("No carro, este botão volta para a interface original da multimídia quando você quiser.");\n'
            '});\n' + alvo2
        )
        h = h.replace(alvo1, novo1, 1).replace(alvo2, novo2, 1)
        with open(caminho_html, "w", encoding="utf-8") as f:
            f.write(h)

    destino_asset = os.path.join(PASTA_ANDROID, "app", "src", "main", "assets", "carro.html")
    os.makedirs(os.path.dirname(destino_asset), exist_ok=True)
    shutil.copy(caminho_html, destino_asset)

    # Copia o ícone da esfera do Jon para res/drawable/ic_launcher.png
    res_dir = os.path.join(PASTA_ANDROID, "app", "src", "main", "res", "drawable")
    os.makedirs(res_dir, exist_ok=True)
    icone_orig = os.path.join(PASTA_JON, "web", "icone-esfera-192.png")
    if os.path.exists(icone_orig):
        shutil.copy(icone_orig, os.path.join(res_dir, "ic_launcher.png"))


def baixar_e_extrair(url, nome_zip, pasta_destino):
    os.makedirs(CACHE_SDK, exist_ok=True)
    arq_zip = os.path.join(CACHE_SDK, nome_zip)
    if not os.path.exists(pasta_destino):
        print(f"  -> Baixando {nome_zip}...")
        urllib.request.urlretrieve(url, arq_zip)
        print(f"  -> Extraindo {nome_zip}...")
        with zipfile.ZipFile(arq_zip, "r") as z:
            z.extractall(pasta_destino)


def encontrar_arquivo(raiz, nome_arq):
    for r, _, files in os.walk(raiz):
        for f in files:
            if f.lower() == nome_arq.lower():
                return os.path.join(r, f)
    return None


def compilar():
    print("========================================================")
    print("  GERANDO APK NATIVO: JonUno9p.apk (FIAT UNO 9\")")
    print("========================================================")
    atualizar_html_ponte()

    jdk_dir = os.path.join(CACHE_SDK, "jdk")
    bt_dir = os.path.join(CACHE_SDK, "build-tools")
    plat_dir = os.path.join(CACHE_SDK, "platform")

    baixar_e_extrair(URL_JDK, "jdk17.zip", jdk_dir)
    baixar_e_extrair(URL_BUILD_TOOLS, "build-tools.zip", bt_dir)
    baixar_e_extrair(URL_PLATFORM, "platform.zip", plat_dir)

    javac = encontrar_arquivo(jdk_dir, "javac.exe")
    java = encontrar_arquivo(jdk_dir, "java.exe")
    keytool = encontrar_arquivo(jdk_dir, "keytool.exe")
    aapt = encontrar_arquivo(bt_dir, "aapt.exe")
    d8_jar = encontrar_arquivo(bt_dir, "d8.jar")
    zipalign = encontrar_arquivo(bt_dir, "zipalign.exe")
    apksigner_jar = encontrar_arquivo(bt_dir, "apksigner.jar")
    android_jar = encontrar_arquivo(plat_dir, "android.jar")

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(os.path.join(BUILD_DIR, "classes"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "gen"), exist_ok=True)

    manifest = os.path.join(PASTA_ANDROID, "app", "src", "main", "AndroidManifest.xml")
    res = os.path.join(PASTA_ANDROID, "app", "src", "main", "res")
    assets = os.path.join(PASTA_ANDROID, "app", "src", "main", "assets")
    java_src = os.path.join(PASTA_ANDROID, "app", "src", "main", "java", "com", "joaovitor", "joncar", "uno")

    print("  [1/5] Empacotando recursos e HTML/Voz do Jon...")
    unsigned_apk = os.path.join(BUILD_DIR, "unaligned.apk")
    subprocess.run([
        aapt, "package", "-f", "-m",
        "-J", os.path.join(BUILD_DIR, "gen"),
        "-M", manifest,
        "-S", res,
        "-A", assets,
        "-I", android_jar,
        "-F", unsigned_apk
    ], check=True)

    print("  [2/5] Compilando código nativo Android (Launcher + BootReceiver)...")
    fontes_java = [
        os.path.join(java_src, "MainActivity.java"),
        os.path.join(java_src, "BootReceiver.java"),
    ]
    r_java = encontrar_arquivo(os.path.join(BUILD_DIR, "gen"), "R.java")
    if r_java:
        fontes_java.append(r_java)

    subprocess.run([
        javac, "-source", "1.8", "-target", "1.8",
        "-encoding", "UTF-8",
        "-bootclasspath", android_jar,
        "-classpath", android_jar,
        "-d", os.path.join(BUILD_DIR, "classes"),
        *fontes_java
    ], check=True)

    print("  [3/5] Convertendo bytecode para Dalvik (classes.dex)...")
    arquivos_class = []
    for r, _, files in os.walk(os.path.join(BUILD_DIR, "classes")):
        for f in files:
            if f.endswith(".class"):
                arquivos_class.append(os.path.join(r, f))

    subprocess.run([
        java, "-cp", d8_jar, "com.android.tools.r8.D8",
        "--lib", android_jar,
        "--output", BUILD_DIR,
        *arquivos_class
    ], check=True)

    with zipfile.ZipFile(unsigned_apk, "a", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(BUILD_DIR, "classes.dex"), "classes.dex")

    print("  [4/5] Alinhando pacote APK (zipalign)...")
    aligned_apk = os.path.join(BUILD_DIR, "aligned.apk")
    subprocess.run([zipalign, "-f", "4", unsigned_apk, aligned_apk], check=True)

    print("  [5/5] Assinando JonUno9p.apk...")
    keystore = os.path.join(CACHE_SDK, "jon_uno.keystore")
    if not os.path.exists(keystore):
        subprocess.run([
            keytool, "-genkeypair", "-v",
            "-keystore", keystore,
            "-alias", "jonuno",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", "jon123456", "-keypass", "jon123456",
            "-dname", "CN=Joao Vitor, OU=JonOS, O=FiatUno, L=SP, ST=SP, C=BR"
        ], check=True)

    apk_final = os.path.join(PASTA_JON, "JonUno9p.apk")
    subprocess.run([
        java, "-jar", apksigner_jar, "sign",
        "--ks", keystore,
        "--ks-pass", "pass:jon123456",
        "--key-pass", "pass:jon123456",
        "--out", apk_final,
        aligned_apk
    ], check=True)

    print("\n========================================================")
    print("  SUCESSO! APK GERADO EM:")
    print(f"  -> {apk_final}")
    print("========================================================")


if __name__ == "__main__":
    compilar()

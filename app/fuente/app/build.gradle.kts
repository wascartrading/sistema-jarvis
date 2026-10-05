plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.wascar.jarvis"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.wascar.jarvis"
        minSdk = 26
        targetSdk = 35
        versionCode = 35
        versionName = "26.0"

        // Su telefono (Galaxy S21 FE) es arm64: una sola ABI = APK ligero.
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")

    // --- App NATIVA (Jetpack Compose, sin WebView) — orden del jefe 04/10/2026
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")

    // Cliente WebSocket para el puente (PC)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // TDLib precompilado (MTProto): Telegram como PUENTE real con la cuenta
    // del jefe (elegido 04/10/2026). Sin NDK; 4 ABIs.
    implementation("io.github.tdlib-android:core:0.1.1")
    implementation("io.github.tdlib-android:ktx:0.1.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
}

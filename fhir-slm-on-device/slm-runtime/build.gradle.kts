plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.kmp.library)
}

group = "dev.ohs.slm"
version = "0.1.0"

kotlin {
    androidLibrary {
        namespace = "dev.ohs.slm"
        compileSdk = 36
        minSdk = 24
    }
    jvm()
    // ponytail: no iOS yet. LiteRT-LM's iOS API is Swift only and in early preview.

    sourceSets {
        commonMain.dependencies {
            implementation(libs.kotlinx.coroutines.core)
        }
        // Android and desktop use the same LiteRT-LM Kotlin API, so they share one source folder.
        androidMain {
            kotlin.srcDir("src/litertMain/kotlin")
            dependencies { api(libs.litertlm.android) }
        }
        jvmMain {
            kotlin.srcDir("src/litertMain/kotlin")
            dependencies { api(libs.litertlm.jvm) }
        }
        jvmTest.dependencies {
            implementation(kotlin("test"))
        }
    }
}

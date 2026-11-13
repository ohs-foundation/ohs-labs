plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.kmp.library)
}

kotlin {
    androidLibrary {
        namespace = "dev.ohs.slm"
        compileSdk = 36
        minSdk = 24
    }
    // ponytail: Android only for now. Add iOS targets when LiteRT-LM's Swift API leaves preview.

    sourceSets {
        commonMain.dependencies {
            implementation(libs.kotlinx.coroutines.core)
        }
        androidMain.dependencies {
            api(libs.litertlm.android)
        }
    }
}

import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
  id("com.android.application")
  id("org.jetbrains.kotlin.android")
  id("org.jetbrains.kotlin.plugin.compose")
}

android {
  namespace = "com.example.ancapp"
  compileSdk = 37

  defaultConfig {
    applicationId = "com.example.ancapp.builda"
    minSdk = 26
    targetSdk = 37
    versionCode = 1
    versionName = "0.1"
  }

  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }

  buildFeatures { compose = true }
}

kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }

dependencies {
  implementation(platform("androidx.compose:compose-bom:2026.03.01"))
  implementation("androidx.core:core-ktx:1.18.0")
  implementation("androidx.activity:activity-compose:1.13.0")
  implementation("androidx.compose.ui:ui")
  implementation("androidx.compose.material3:material3")
}

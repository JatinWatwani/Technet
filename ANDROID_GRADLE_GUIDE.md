# Android Gradle App Guide for Vigilio

The Vigilio Mobile Courier Partner App is now fully configured as a native **Android Gradle Project** inside `frontend/android/`.

---

## Project Structure

```
frontend/android/
├── build.gradle               # Root Gradle configuration
├── settings.gradle            # Gradle module definitions
├── variables.gradle           # SDK & AndroidX dependency versions
├── gradlew                    # Unix Gradle wrapper executable
├── gradlew.bat                # Windows Gradle wrapper script
├── gradle/wrapper/            # Gradle wrapper distribution
└── app/
    ├── build.gradle           # App-level Gradle plugin & dependencies
    └── src/main/
        ├── AndroidManifest.xml # Android app manifest (permissions, intent filters)
        ├── java/com/vigilio/partner/MainActivity.java # Native Android activity
        ├── res/               # App icons, splash screens, strings.xml
        └── assets/public/     # Synced production mobile app bundle
```

---

## How to Open in Android Studio

1. Open **Android Studio**.
2. Click **"Open"** and choose the `frontend/android` folder.
3. Android Studio will automatically sync the Gradle project (`build.gradle` and `app/build.gradle`).
4. Select an Android Emulator or connected physical phone and click **Run (Shift + F10)**.

Alternatively, from the terminal:
```bash
cd frontend
npm run android:open
```

---

## How to Build the APK using Gradle Wrapper

### On Windows (PowerShell / CMD):
```bash
cd frontend\android
.\gradlew.bat assembleDebug
```
The compiled debug APK will be located at:
`frontend/android/app/build/outputs/apk/debug/app-debug.apk`

### On macOS / Linux:
```bash
cd frontend/android
./gradlew assembleDebug
```

---

## How to Sync Web & UI Changes into Android

Whenever you update the React mobile UI, sync the changes to the Android native project with:
```bash
cd frontend
npm run build
npm run android:sync
```

---

## Native Android Features Enabled

- **Geospatial GPS**: Native Android Location services compatible with Leaflet maps.
- **Hardware Acceleration**: Smooth 60 FPS transitions and haptic swipe sliders.
- **Offline Storage**: Pre-cached PWA and assets bundled directly inside the APK (`assets/public/`).

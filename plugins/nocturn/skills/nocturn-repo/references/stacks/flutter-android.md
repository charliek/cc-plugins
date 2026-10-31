# Flutter and Android

Standards: `conventions.yaml` and `rules.yaml` in the nocturn install. Flutter
has no baseline (`flutter: null` in `baseline.yaml`); the rules grade time
instead. Check the `flutter:` table in `rules.yaml` for current numbers: it
changes about four times a year.

## Where the pins come from

| Pin | Source |
|---|---|
| `flutter` | `subosito/flutter-action`'s `flutter-version` in a workflow. This builds the artifact, so it is the pin. Also `.mise.toml`. |
| `gradle` | `distributionUrl` in `gradle-wrapper.properties` (`.../gradle-8.14-bin.zip`) |
| `agp` | the `com.android.application` (or `com.android.library`) plugin line with a version in `settings.gradle(.kts)` |
| `kotlin` | the `org.jetbrains.kotlin.android` plugin line with a version in `settings.gradle(.kts)` |

Not pins: `pubspec.yaml` `sdk:`, the lock file's `sdks`, `.metadata`. Gradle
version catalogs (`libs.versions.toml`) aren't read, nor is the JDK (use 17,
Flutter's floor). The plugin line must look like
`id("com.android.application") version "8.11.1" apply false`. Pin exact
versions: `3.47.8`, not `3.47` or `stable`; mise's `3.x.y-stable` reads as
unpinned. If workflows pin different Flutter versions, that is
`inconsistent` (warn): keep them equal.

## How they're graded

- **Flutter (`flutter-runtime`)**: the time since a *later minor* shipped,
  not the pin's age. Fixes go only to current stable. 30 days after the next
  minor's first release: warn (plan). 120 days: critical (act). The current
  minor is OK at any age. Move to the newest stable minor soon after it ships;
  patch bumps inside a minor are fine.
- **Flutter SDK advisories** (`flutter-sdk-advisory`): a high or critical
  advisory affecting the pin (patched version above it) is act at once. A
  patch bump within the minor often clears it.
- **Gradle, AGP, Kotlin** (`gradle-runtime`, `agp-runtime`, `kotlin-runtime`):
  graded against the pin's floors in the `flutter:` table of `rules.yaml`, not
  upstream latest. Latest Gradle can be past what Flutter supports. Below the
  `error` floor is critical (the release build fails); below `warn` is warn.
  When the Flutter pin's minor has no row in the table, the result is an info
  finding saying the table needs a row (a nocturn-side fix, not a repo one).
  Multiple Flutter pins: the highest fixed one is used.
- **Play target SDK** (`play-target-sdk`): `android/app/build.gradle(.kts)`
  `targetSdk` (or `flutter.targetSdkVersion`, which the table resolves per
  minor) must meet Google Play's requirement before its deadline. Within 60
  days or past: act; within 180: plan.
- **pub packages** (`libraries-pub`, direct only): warn when 180 days past a
  later release (prod scope), when discontinued, or when retracted. Info at
  90 days. Transitive packages aren't time-graded. deps.dev has no pub, so
  pub.dev dates are used.

## Conform to

- A concrete `flutter-version` in every workflow that builds, all equal (and
  equal to `.mise.toml` if present).
- `gradle-wrapper.properties`, `settings.gradle(.kts)` at or above the
  `warn` floor for your Flutter minor. To bump: edit the wrapper version
  (`./gradlew wrapper --gradle-version <x.y.z>`) and the plugin lines, then
  build the app.
- `dependabot-config`: `pub` at each `pubspec.yaml` directory,
  `github-actions` at `/`; add `bundler` only if Dependabot is wanted for
  Gemfile.lock (it isn't required by the check).
- Internal libraries: `stridelabs-flutter` (git dependency by tag, warn at 1
  tag behind): bump its tag.
- Shared: `gate-command`, `ci-on-pull-requests`, `agent-instructions`.

## File mapping

```yaml
targets:
  android:
    kind: mobile
    ships: [mobile/pubspec.lock]
lockfiles:
  mobile/android/Gemfile.lock: { role: build-tool }   # fastlane uploads the bundle
```

- The Flutter app's `pubspec.lock` goes in a `kind: mobile` target's `ships`.
  A mobile target has no `cloud_run` or `released`.
- fastlane's `Gemfile.lock` is `build-tool`.
- Tag the project `flutter` in the central `projects.yaml`.
- Run `nocturn repo inspect` to see the detected pins and `android_apps`
  (each app's target SDK, or `flutter.targetSdkVersion`) before and after
  bumping.

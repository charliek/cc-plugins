#!/usr/bin/env bash
# ============================================================================
# TEMPLATE — do not run from the plugin. Copy this into an app repo as
#   .claude/skills/drive-<app>/scripts/launch-and-connect.sh
# then edit ONLY the CONFIG block below for that app. Everything under
# "---- generic body ----" is app-agnostic and should be copied verbatim.
#
# Launch a StrideLabs Flutter client in debug mode and register it with
# Marionette. Leaves `flutter run` running in the background (prints its PID +
# log path) so an agent can drive the app, then hot-reload after edits.
# Debug build only.
#
# Usage: launch-and-connect.sh [device] [instance-name]
#   device defaults to the first entry of DEVICES; instance to INSTANCE_DEFAULT.
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# CONFIG — edit these per app.
# ---------------------------------------------------------------------------

# Instance name registered with Marionette (also the default, and used in the
# printed next-steps). Alphanumeric with hyphens/underscores: [a-zA-Z0-9_-]+.
INSTANCE_DEFAULT="my-app"

# App directory RELATIVE to the git toplevel. Empty ("") for a single-app repo
# where the Flutter project is the repo root (e.g. shed-mobile). Otherwise the
# subdir, e.g. "mobile" (slaudio-mobile) or "apps/flutter_client" (tapper).
APP_SUBDIR=""

# Supported `flutter run -d` device ids, for the usage hint only. First = default.
DEVICES=(macos linux android)

# dart-define files passed at launch, RELATIVE to the app dir, in order (later
# wins). Typically the checked-in env/dev.json (config + DEV_AUTH:true) plus the
# gitignored env/dev.local.json (TEST_USER_EMAIL/PASSWORD for headless dev login).
DEFINE_FILES=(env/dev.json env/dev.local.json)

# Subset of DEFINE_FILES that MUST exist — the script fails loudly if one is
# missing (e.g. env/dev.local.json, without which the dev-login button won't
# render). Leave empty () to make all define files optional (included only when
# present). List paths exactly as they appear in DEFINE_FILES.
REQUIRED_DEFINE_FILES=(env/dev.local.json)

# Android only: TCP port to `adb reverse` to every attached device so the app can
# reach a host-local backend (localhost:PORT). Empty ("") disables adb reverse.
ADB_REVERSE_PORT=""

# ---------------------------------------------------------------------------
# ---- generic body (copy verbatim) ----
# ---------------------------------------------------------------------------

# Kill the background `flutter run` if we exit before a successful registration
# (URI never appears, or `marionette register` fails under `set -e`). After we
# register, we deliberately leave it running for the agent to drive.
RUN_PID=""
KEEP_RUNNING_ON_EXIT=0
cleanup() {
  if [ "$KEEP_RUNNING_ON_EXIT" -eq 0 ] && [ -n "${RUN_PID:-}" ]; then
    kill "$RUN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

DEVICE="${1:-${DEVICES[0]}}"
INSTANCE="${2:-$INSTANCE_DEFAULT}"
MARIONETTE="${MARIONETTE:-$(command -v marionette || echo "$HOME/.pub-cache/bin/marionette")}"

REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
if [ -n "$APP_SUBDIR" ]; then APP="$REPO/$APP_SUBDIR"; else APP="$REPO"; fi
LOG="$(mktemp -t "${INSTANCE}-flutter-XXXXXX").log"

if [ ! -x "$MARIONETTE" ] && ! command -v "$MARIONETTE" >/dev/null 2>&1; then
  echo "marionette CLI not found. Install: dart pub global activate marionette_cli" >&2
  echo "and ensure ~/.pub-cache/bin is on PATH (or set MARIONETTE=/path/to/marionette)." >&2
  exit 1
fi

# Required define files must exist, or headless dev login won't be available.
for f in "${REQUIRED_DEFINE_FILES[@]:-}"; do
  [ -z "$f" ] && continue
  if [ ! -f "$APP/$f" ]; then
    echo "Missing $APP/$f — the dev-login button won't appear." >&2
    echo "Copy its .example and fill in the test-user creds from ../slauth/test-users.md" >&2
    echo "before driving the login flow." >&2
    exit 1
  fi
done

# Assemble the dart-define flags: required files are guaranteed present; optional
# ones are included only when they exist.
DEFINES=()
for f in "${DEFINE_FILES[@]}"; do
  if [ -f "$APP/$f" ]; then
    DEFINES+=(--dart-define-from-file="$f")
  fi
done

# Android needs the backend reverse-tunnelled to the device/emulator. Reverse the
# configured port on EVERY connected device and FAIL if none succeeds — a silently
# missing tunnel means the app launches but every API call dies.
if [ "$DEVICE" = "android" ] && [ -n "$ADB_REVERSE_PORT" ]; then
  reversed=0
  for serial in $(adb devices | awk 'NR>1 && $2=="device" {print $1}'); do
    if adb -s "$serial" reverse "tcp:$ADB_REVERSE_PORT" "tcp:$ADB_REVERSE_PORT"; then
      reversed=1
    else
      echo "adb reverse failed for device $serial" >&2
    fi
  done
  if [ "$reversed" -ne 1 ]; then
    echo "No Android device accepted 'adb reverse tcp:$ADB_REVERSE_PORT' — check 'adb devices'" >&2
    echo "(unauthorized/offline devices, or no device attached)." >&2
    exit 1
  fi
fi

echo "Launching Flutter ($DEVICE), logging to $LOG ..."
( cd "$APP" && exec flutter run -d "$DEVICE" "${DEFINES[@]}" ) >"$LOG" 2>&1 &
RUN_PID=$!

# Wait for the Dart VM Service URI (http://127.0.0.1:PORT/TOKEN/) in the log.
# Anchor on Flutter's "Dart VM Service" line so we never grab the DevTools URL,
# which is also an http://127.0.0.1 address printed around the same time.
URI=""
for _ in $(seq 1 150); do
  URI="$(grep -a 'Dart VM Service' "$LOG" 2>/dev/null \
          | grep -oE 'http://127\.0\.0\.1:[0-9]+/[A-Za-z0-9_=/-]+' | head -1 || true)"
  [ -n "$URI" ] && break
  if ! kill -0 "$RUN_PID" 2>/dev/null; then
    echo "flutter run exited before printing a VM Service URI. Log:" >&2
    tail -n 40 "$LOG" >&2
    exit 1
  fi
  sleep 2
done
if [ -z "$URI" ]; then
  echo "Timed out waiting for the VM Service URI. See $LOG" >&2
  exit 1   # trap cleanup() kills RUN_PID
fi

# Convert http://host:port/token/ -> ws://host:port/token/ws
WS="$(printf '%s' "$URI" | sed -e 's#^http#ws#' -e 's#/\{0,1\}$#/ws#')"

echo "VM Service: $WS"
"$MARIONETTE" register "$INSTANCE" "$WS"
KEEP_RUNNING_ON_EXIT=1   # registered — leave flutter run alive for the agent

cat <<EOF

Connected as instance "$INSTANCE". flutter run is PID $RUN_PID (log: $LOG).

Next steps (see the per-app skill's key map for the full key inventory):
  $MARIONETTE -i $INSTANCE get-interactive-elements
  $MARIONETTE -i $INSTANCE tap --key login-dev-sign-in            # headless dev login
  $MARIONETTE -i $INSTANCE get-logs | grep -E 'MSTATE|MRESULT' | tail -5
  $MARIONETTE -i $INSTANCE take-screenshots --output ./$INSTANCE.png

Cleanup:
  kill $RUN_PID
  $MARIONETTE unregister $INSTANCE
EOF

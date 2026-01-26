# CLIENT_ANDROID.md

## Purpose

Android client is the main client for ZSUS at the current stage.

This is NOT a full native Android app.
It is a thin APK shell over the existing web client, designed for:
- real usage by people
- demos
- fast iteration and feedback

No Google Play. Manual APK distribution only.


## Core principles

- WebView-based client
- One Activity
- No duplication of backend or frontend logic
- Same UX and behavior as web client
- Simplicity over completeness
- No premature optimizations


## UI / UX decisions

- No browser UI (no address bar)
- Portrait orientation only
- Fullscreen mode (non-aggressive; system bars may remain if device enforces them)
- Fast launch:
  - no splash screen
  - app opens directly into usable interface
- Back button:
  - closes the app
  - no browser-like navigation history
- Keep screen on:
  - enabled by config
  - intended for hands-busy / workshop usage


## WebView behavior

- Loads fixed URL:
  https://<domain>/zsus/
- URL is hardcoded but stored in a dedicated config file/class
- Changing server URL requires rebuilding APK (acceptable for MVP)

- No offline mode
- No network availability checks
- If service is unavailable, web UI handles it as-is


## Voice input

- Uses Web Speech API via WebView
- Same implementation as web client
- No native STT
- No additional UX warnings or fallbacks

Permissions:
- RECORD_AUDIO
- INTERNET

Permission handling:
- Minimal
- Only what is required for Web Speech to function
- No additional explanations or preflight warnings


## User identification

- user_id parameter is supported by web client
- Android client does NOT set or manage user_id at this stage
- WebView loads plain `/zsus/` without query parameters
- user_id support may be added later without breaking changes


## Android versions & support

- Target modern Android devices
- No explicit support for very old devices
- If Web Speech does not work on a specific device, this is acceptable at MVP stage


## Repository structure

- Android client lives inside the main ZSUS repository
- Suggested path:
  /android

- This is intentional (monorepo):
  - one project
  - multiple clients
  - shared lifecycle

Gradle and Android build artifacts must be excluded via .gitignore.


## Explicit non-goals (current stage)

- No native STT
- No push notifications
- No background services
- No offline mode
- No authentication
- No auto-update of APK
- No Play Store publishing

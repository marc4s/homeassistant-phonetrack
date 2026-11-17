# homeassistant-phonetrack
PhoneTrack custom device_tracker component for Home Assistant.

## Purpose
The purpose of this custom component for [Home-Assistant](https://home-assistant.io) is to track GPS devices that are using a PhoneTrack-OC backend. PhoneTrack-OC is an app for Nextcloud/Owncloud exposing an API compatible with Owntracks / µLogger / GPSLogger and many more to store your positions in Nextcloud.

## Inspired by
This project was inspired by the custom device_tracker component quickly created by @Phyks here:
https://community.home-assistant.io/t/custom-device-tracker-not-firing-at-expected-interval/45100

I just took his code, converted it top the new(er) structure and adjusted it heavily inspired by the Google Shared Location device tracker.

- credits go to @Phyks here. Released this updated coded under Apache 2.0 to protect his code a bit as he did not stated a license at all.

2026-11 and credits to j1nx for the initial phonetrack component for homeassistant. as this gets incompatible in homeassistant with 2027.5 I made some changes

regards

## Setup instructions
- manually remove the old phonetrack component from custom_components and comment out your old configuration from configuration.yaml

### Enabling the custom_component
- Add this repo-url https://github.com/marc4s/homeassistant-phonetrack to your marketplace and install 

### Add/Setup the integration
- use the setup flow
URL should be something like
https://NEXTCLOUDHOST/index.php/apps/phonetrack/api/getlastpositions/
- report issues if you have some


## ✅ Completed Improvements

This version includes the following major improvements:

- **Config Flow Integration**: Set up PhoneTrack through the Home Assistant UI instead of YAML
- **Reconfigure Support**: Reconfigure the integration through the UI without YAML changes
- **Improved Reconnection Logic**: Automatic reconnection with configurable interval (default 300s) when server is unavailable
- **Modern Device Tracker API**: Migrated to the new `TrackerEntity` API that includes:
  - `tracking_type` attribute set to `position` for GPS-based tracking
  - Proper state attributes like `in_zones`, `latitude`, `longitude`, `location_accuracy`
  - Compatibility with Home Assistant 2027+ (legacy device tracker removal and battery_level to sensor)



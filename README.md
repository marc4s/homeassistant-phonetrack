# homeassistant-phonetrack
PhoneTrack custom device_tracker component for Home Assistant.

## Purpose
The purpose of this custom component for [Home-Assistant](https://home-assistant.io) is to track GPS devices that are using a PhoneTrack-OC backend. PhoneTrack-OC is an app for Nextcloud/Owncloud exposing an API compatible with Owntracks / µLogger / GPSLogger and many more to store your positions in Nextcloud.

## Inspired by
This project was inspired by the custom device_tracker component quickly created by @Phyks here:
https://community.home-assistant.io/t/custom-device-tracker-not-firing-at-expected-interval/45100

I just took his code, converted it top the new(er) structure and adjusted it heavily inspired by the Google Shared Location device tracker.

ALL credits go to @Phyks here. Released this updated coded under Apache 2.0 to protect his code a bit as he did not stated a license at all.

## Setup instructions
### Copying into custom_components folder
Create a directory `custom_components` in your Home-Assistant configuration directory.
Copy the whole [phonetrack](./phonetrack) folder from this project into the newly created directory `custom_components`.

The result of your copy action(s) should yield a directory structure like so:

```
.homeassistant/
|-- custom_components/
|   |-- phonetrack/
|       |-- __init__.py
|       |-- device_tracker.py
|       |-- manifest.json
```

### Enabling the custom_component
In order to enable this custom device_tracker component, add this code snippet to your Home-Assistant `configuration.yaml` file:

```yaml
device_tracker:
  - platform: phonetrack
    url: https://<NEXTCLOUD_URL>/index.php/apps/phonetrack/api/getlastpositions/
    token: <SHARED_VIEW_TOKEN>

    # Optional. Default is 5 minutes.
    update_time_minutes: 0 
    update_time_seconds: 30
    
    devices:
      - <DEVICE_NAME>
```

Please use [secrets](https://www.home-assistant.io/docs/configuration/secrets/) within Home-Assistant to store sensitive data like API Tokens.

## ✅ Completed Improvements

This version includes the following major improvements:

- **Config Flow Integration**: Set up PhoneTrack through the Home Assistant UI instead of YAML
- **Reconfigure Support**: Reconfigure the integration through the UI without YAML changes
- **Improved Reconnection Logic**: Automatic reconnection with configurable interval (default 300s) when server is unavailable
- **Modern Device Tracker API**: Migrated to the new `TrackerEntity` API that includes:
  - `tracking_type` attribute set to `position` for GPS-based tracking
  - Proper state attributes like `in_zones`, `latitude`, `longitude`, `location_accuracy`
  - Compatibility with Home Assistant 2027+ (legacy device tracker removal)

## TODO

Additional improvements for the future:

- Better zone detection and handling
- Device registry integration enhancements
- More detailed error handling and recovery

## Troubleshooting
I don't know how to code in Python (yet). This is just copy & paste work and using Google (a lot) debugging all errors I do not understand, while doing stuff I don't know. I have some more Python projects on the shelf, so whenever I start leaning that code a bit more, I will look into making it better.

Till then, feel free to fork and create PRs.

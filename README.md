# Nightscout Notifier

An app to notify your preferred emergency contacts in case your blood glucose values from Nightscout are  out of range.
This app uses the nexmo dispatch api and is written in Flask.

If your values are out of range, initially a SMS will be sent. If the values are significantly low or high, a phone call will call you and your preferred contact and will read the value over the phone.

# Scout: Nexmo + Nightscout

An app to notify your preferred emergency contacts in case your blood glucose values from Nightscout are  out of range.
This app uses the Nexmo messages and voice api's and is written in Flask.

If your values are out of range (significantly low or high) You will get a phone call alerting you and reading your blood glucose over the phone. In the event of not answering the call your preferred emergency contact(s) will receive an SMS notifying them you are out of range.

## Context

I have type 1 diabetes. With all the amazing open source initiatives, i added a way to notify my contacts should i become unresponsive due to being too high or too low. All the data comes from my nightscout dasbhoard:(If you want to check my blood glucose values in real time go to https://dianux.superdi.dev)

![Nightscout Dashboard](nightscout.png)


Although the initial state of this app is very basic, it's work in progress and you're more than welcome to contribute. The idea is to add more configuration options and improve the UI.

![Scout Dashboard](dashboard.png)





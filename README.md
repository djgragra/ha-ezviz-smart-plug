# EZVIZ Smart Plug for Home Assistant

Control EZVIZ smart plugs (the ones in the EZVIZ app, "Socket" category) from Home Assistant, through the EZVIZ cloud.

The core Home Assistant `ezviz` integration supports cameras, lights and sirens but **not smart plugs**. This integration fills that gap. It uses [`pyezvizapi`](https://pypi.org/project/pyezvizapi/), the same library as the core integration, so it keeps working as Home Assistant updates it.

## Features
- One `switch` (outlet) per plug, with on/off and the real state from the cloud.
- Plugs are detected by the **device category** reported by EZVIZ, not by the serial number, so every plug model in your account is picked up.
- Plugs added to the account later appear automatically; offline plugs are shown as unavailable.
- Sign in with e-mail and password, **MFA verification code** supported, automatic **re-authentication** when the session expires. The password is never stored, only the session tokens.
- Works next to the core `ezviz` integration with the same account.
- Diagnostics download with credentials, serial numbers and MAC addresses redacted.
- English and Italian translations.

Not included (yet): power/energy measurement, schedules, local (LAN) control. Everything goes through the EZVIZ cloud, polled every 30 seconds.

## Installation
### HACS (custom repository)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/djgragra/ha-ezviz-smart-plug`, type **Integration**.
2. Install **EZVIZ Smart Plug** and restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *EZVIZ Smart Plug*.

### Manual
Copy `custom_components/ezviz_smart_plug` into your `config/custom_components` folder and restart.

## Configuration
Enter the e-mail and password of your EZVIZ app account. The API server defaults to Europe; the region is detected at login. If your account has two-factor authentication, EZVIZ sends a code that you enter in the next step.

## Notes and limitations
- Tested on Home Assistant 2026.10 with one plug (serial starting with `Q`). Other plug models should work because detection does not depend on the serial, but they have not been tested: please open an issue with the model and a diagnostics file if something is off.
- Each login to the EZVIZ cloud may sign out other sessions of the same account on some regions; if you see repeated re-authentication requests, use a dedicated EZVIZ account shared with your plugs.
- If you were using the older `ezviz_plug` custom integration, this one replaces it (different domain, so entities are new).

## Italiano
Integrazione per le **prese smart EZVIZ** (categoria "Socket" dell'app EZVIZ), tramite cloud. L'integrazione `ezviz` del core non gestisce le prese. Si installa da HACS come repository personalizzato (`https://github.com/djgragra/ha-ezviz-smart-plug`, tipo Integrazione), poi Impostazioni → Dispositivi e servizi → Aggiungi integrazione → *EZVIZ Smart Plug*. Vengono salvati solo i token di sessione, non la password; il codice di verifica (MFA) è supportato. Le prese sono rilevate per categoria, non per prefisso del seriale. Per ora solo accensione/spegnimento e stato; niente misura di potenza.

## Development
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

## Credits and license
MIT, see [LICENSE](LICENSE). Built on [`pyezvizapi`](https://github.com/RenierM26/pyEzvizApi). Thanks to [@khal3d](https://github.com/khal3d/homeassistant-ezviz-smart-plug) for the original plug integration this one replaces. Not affiliated with EZVIZ or Hikvision.

The EZVIZ name and logo (`custom_components/ezviz_smart_plug/brand/`) are trademarks of their owner, taken from the Home Assistant brands repository and used only to identify the service this integration works with. They are not covered by the MIT license.

## Support
This integration is free and will stay free. If it saved you time, you can leave a tip on [Ko-fi](https://ko-fi.com/onairgarage), a thank-you and nothing more. Bug reports and test results on other plug models are just as welcome: open an [issue](https://github.com/djgragra/ha-ezviz-smart-plug/issues).

*Italiano:* l'integrazione è gratuita e resta tale. Se ti è stata utile puoi lasciare una mancia su [Ko-fi](https://ko-fi.com/onairgarage), un grazie e basta. Segnalazioni e prove su altri modelli di presa sono altrettanto gradite.

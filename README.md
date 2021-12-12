# Frank Energie Custom Component voor Home Assistant
Middels deze integratie wordt de huidige prijsinformatie van Frank Energie beschikbaar gemaakt binnen Home Assistant.

De waarden van de prijssensoren kunnen bijvoorbeeld gebruikt worden om apparatuur te schakelen op basis van de huidige energieprijs.

### Disclaimer
Deze integratie is nog in een enorm vroege status. Prijsinformatie wordt automatisch gedownload, maar de waarden van sensoren worden niet automatisch ieder uur bijgewerkt. Voor nu is dit wel te realiseren middels bijvoorbeeld onderstaande automatisering:
```
alias: Update electriciteitsprijs
description: 'Werk op het hele uur de huidige energieprijs bij'
trigger:
  - platform: time_pattern
    minutes: '0'
    seconds: '0'
action:
  - service: homeassistant.update_entity
    target:
      entity_id:
        - sensor.current_electricity_price_all_in
mode: single
```
## Installatie
Plaats de map `frank_energie` uit de map `custom_components` binnen deze repo in de `custom_components` map van je Home Assistant installatie.

### HACS

Installatie via HACS is mogelijk door deze repository toe te voegen als [custom repository](https://hacs.xyz/docs/faq/custom_repositories) met de categorie 'Integratie'.

### Configuratie

De plugin en sensoren worden per stuk geconfigureerd in `configuration.yaml`.

```
sensor:
  - platform: frank_energie
      display_options:
        - gas_markup
        - elec_markup
        - gas_market
        - elec_market
        - gas_min
        - gas_max
        - elec_min
        - elec_max
        - elec_avg
```

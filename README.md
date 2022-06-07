# Frank Energie Custom Component voor Home Assistant
Middels deze integratie wordt de huidige prijsinformatie van Frank Energie beschikbaar gemaakt binnen Home Assistant.

De waarden van de prijssensoren kunnen bijvoorbeeld gebruikt worden om apparatuur te schakelen op basis van de huidige energieprijs.

## Installatie
Plaats de map `frank_energie` uit de map `custom_components` binnen deze repo in de `custom_components` map van je Home Assistant installatie.

### HACS
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Installatie via HACS is mogelijk door deze repository toe te voegen als [custom repository](https://hacs.xyz/docs/faq/custom_repositories) met de categorie 'Integratie'.

### Configuratie

De plugin en sensoren worden per stuk geconfigureerd in `configuration.yaml`.

```
sensor:
  - platform: frank_energie
    display_options:
      - gas_market
      - gas_tax
      - gas_markup
      - elec_market
      - elec_tax
      - elec_markup
      - gas_min
      - gas_max
      - elec_min
      - elec_max
      - elec_avg
```

# Frank Energie Custom Component voor Home Assistant
Middels deze integratie wordt de huidige prijsinformatie van Frank Energie beschikbaar gemaakt binnen Home Assistant.

De waarden van de prijssensoren kunnen bijvoorbeeld gebruikt worden om apparatuur te schakelen op basis van de huidige energieprijs.

## Installatie
Plaats de map `frank_energie` uit de map `custom_components` binnen deze repo in de `custom_components` map van je Home Assistant installatie.

### HACS
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Installatie via HACS is mogelijk door deze repository toe te voegen als [custom repository](https://hacs.xyz/docs/faq/custom_repositories) met de categorie 'Integratie'.

### Configuratie

<a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=frank_energie" class="my badge" target="_blank">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg">
</a>

De Frank Energie integratie kan worden toegevoegd via de 'Integraties' pagina in de instellingen.
Vervolgens kunnen sensoren per stuk worden uitgeschakeld of verborgen indien gewenst.

#### Let op!

Indien je deze plugin al gebruikte en hebt ingesteld via `configuration.yaml` dien je deze instellingen te verwijderen en Frank Energie opnieuw in te stellen middels de config flow zoals hierboven beschreven.

#### Inloggen

Tijdens het instellen van de integratie wordt je gevraagd of je wilt inloggen. Als je niet inlogd krijg je de huidige energietarieven van Frank Energie als sensoren, als je wel inlogd komen hier ook sensoren voor verwachte en werkele kosten voor deze maand tot nu toe.

### Gebruik

Een aantal sensors hebben een `prices` attribuut die alle bekende prijzen bevat. Dit kan worden gebruikt om zelf met een template nieuwe sensors te maken.

Voorbeeld om de hoogst bekende prijs na het huidige uur te bepalen:
```
{{ state_attr('sensor.current_electricity_price_all_in', 'prices') | selectattr('from', 'gt', now()) | max(attribute='price') }}
```

Laagste prijs vandaag:
```
{{ state_attr('sensor.current_electricity_price_all_in', 'prices') | selectattr('till', 'le', now().replace(hour=23)) | min(attribute='price') }}
```

Laagste prijs in de komende zes uren:
```
{{ state_attr('sensor.current_electricity_price_all_in', 'prices') | selectattr('from', 'gt', now()) | selectattr('till', 'lt', now() + timedelta(hours=6)) | min(attribute='price') }}
```

### Grafiek (voorbeelden)
Middels [apex-card](https://github.com/RomRider/apexcharts-card) is het mogelijk de toekomstige prijzen te plotten:

#### Voorbeeld 1 - Alle data

![Apex graph voorbeeld 1](/images/example_1.png "Voorbeeld 1")

```yaml 
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: Nu
header:
  show: true
  title: Energieprijs per uur (€/kwh)
series:
  - entity: sensor.current_electricity_price_all_in
    show:
      legend_value: false
    stroke_width: 2
    float_precision: 3
    type: column
    opacity: 0.3
    color: '#03b2cb'
    data_generator: |
      return entity.attributes.prices.map((record, index) => {
        return [record.from, record.price];
      });
```

#### Voorbeeld 2 - Komende 10 uur

![Apex graph voorbeeld 2](/images/example_2.png "Voorbeeld 2")

```yaml
type: custom:apexcharts-card
graph_span: 14h
span:
  start: hour
  offset: '-3h'
now:
  show: true
  label: Nu
header:
  show: true
  show_states: true
  colorize_states: true
yaxis:
  - decimals: 2
    min: 0
    max: '|+0.10|'
series:
  - entity: sensor.current_electricity_price_all_in
    show:
      in_header: raw
      legend_value: false
    stroke_width: 2
    float_precision: 4
    type: column
    opacity: 0.3
    color: '#03b2cb'
    data_generator: |
      return entity.attributes.prices.map((record, index) => {
        return [record.from, record.price];
      });
```

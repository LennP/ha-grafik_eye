# Lutron Grafik Eye 3000 Home Assistant

Home Assistant integration that uses Telnet to connect to a Lutron Grafik Eye 3000. The integration uses [Select](https://www.home-assistant.io/integrations/select/) entities to allow you to change the scene for different control units. There is also an update interval which is used to poll and update the select entities.

The manual of the Grafik Eye 3000 can be found [here](https://assets.lutron.com/a/documents/032518_eu.pdf).

# Configuration

The integration is configured using the `configuration.yaml` file.
```yaml
grafik_eye:
  login: nwk # default login, or nkw2
  ip: 192.168.178.14
  port: 23 # default Telnet port
  control_units:
    - name: Living room
      id: 1
    - name: Kitchen
      id: 2
    - name: Porch
      id: 3
  scenes:
    - name: Off
      id: 0
    - name: Scene 1
      id: 1
    - name: Scene 2
      id: 2
    - name: Scene 3
      id: 3
    - name: Scene 4
      id: 4
```
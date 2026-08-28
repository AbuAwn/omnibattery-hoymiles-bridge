#!/command/with-contenv bashio

bashio::log.info "Starting Omnibattery Hoymiles Bridge..."

# El archivo de configuración de Home Assistant Add-on se monta automáticamente en /data/options.json
# Nuestro main.py ya está programado para buscarlo allí si existe.

bashio::log.info "Executing main.py"
python3 main.py

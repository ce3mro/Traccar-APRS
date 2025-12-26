<h2><strong>Integracion de Traccar API a APRS-IS</strong></h2>
<p>Mediante este script es posible enviar la posicion de un dispositivo GPS tipo TK-403 4G o similares que se encuentre configurado en un servidor Traccar a la red de posicionamiento de radioaficionados APRS-IS para luego ser vista en sitios como https://aprs.fi entre otros.<br />Dicha posicion solo se envia cuando el GPS cuenta con la se&ntilde;al de motor encendido, para asi optimizar el envio de paquetes a la red APRS y no saturarla de los mismos. Una vez que se detiene el motor se envia un ultimo paquete de posicion indicando dicho estado a la red APRS.</p>
<p><strong>Para integrar el script como servicio en Debian debe seguir los siguientes pasos:</strong></p>
<p><strong>Pre-requisitos</strong><br />sudo apt update<br />sudo apt install python3 python3-pip</p>
<p><strong>Crear el directorio</strong><br />sudo mkdir -p /opt/traccar-aprs</p>
<p><strong>Guardar el archivo traccar-aprs.py en dicho directorio</strong></p>
<p><strong>Otorgar permisos</strong><br />sudo chmod +x /opt/traccar-aprs/traccar-aprs.py</p>
<p><strong>Crear el Servicio</strong><br />sudo nano /etc/systemd/system/traccar-aprs.service</p>
<p><strong>Pegar el siguiente codigo en el editor</strong></p>
<p><em>[Unit]</em><br /><em>Description=Traccar to APRS-IS Gateway</em><br /><em>After=network-online.target</em><br /><em>Wants=network-online.target</em></p>
<p><em>[Service]</em><br /><em>Type=simple</em><br /><em>User=TU_USUARIO</em><br /><em>WorkingDirectory=/opt/traccar-aprs</em><br /><em>ExecStart=/usr/bin/python3 /opt/traccar-aprs/traccar-aprs.py</em><br /><em>Restart=always</em><br /><em>RestartSec=10</em><br /><em>StandardOutput=journal</em><br /><em>StandardError=journal</em></p>
<p><em>[Install]</em><br /><em>WantedBy=multi-user.target</em></p>
<p><strong>Reemplazar User=TU_USUARIO por el usuario que ejecutara el servicio</strong></p>
<p><strong>Recargar systemd</strong><br />sudo systemctl daemon-reexec<br />sudo systemctl daemon-reload</p>
<p><strong>Habilitar el Servicio</strong><br />sudo systemctl enable traccar-aprs</p>
<p><strong>Iniciar el Servicio</strong><br />sudo systemctl start traccar-aprs</p>
<p><strong>Ver el Estado del Servicio</strong><br />sudo systemctl status traccar-aprs</p>
<p><strong>Revisar LOGs</strong><br />journalctl -u traccar-aprs -f</p>
<p><strong>Para Detener o Reiniciar</strong><br />sudo systemctl stop traccar-aprs<br />sudo systemctl restart traccar-aprs</p>
<p><strong>Recuerda editar el archivo traccar-aprs-py con los datos de tu servidor Traccar y tu informacion de radioaficionado (Se&ntilde;al de Llamada y Passcode) ademas de indicar el deviceid del GPS que deseas enviar a la red APRS.</strong></p>

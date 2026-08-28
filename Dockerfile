ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for python packages
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# Set workdir
WORKDIR /usr/src/app

# Copy requirements and install
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY mqtt_client.py main.py run.sh ./

# Make run.sh executable
RUN chmod a+x run.sh

# Start the application
CMD [ "./run.sh" ]

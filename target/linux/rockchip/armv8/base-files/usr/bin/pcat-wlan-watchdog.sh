#!/bin/sh

WLAN_SDIO_PATH="/sys/bus/mmc/devices/mmc2:0001"
SDIO_DEV="fe2c0000.mmc"

if [ ! -d "${WLAN_SDIO_PATH}" ]; then
    exit 0
fi

while true; do
    COUNT=0

    ATH10K_SDIO_MODULE="$(grep ath10k_sdio /proc/modules)"
    if [ x"${ATH10K_SDIO_MODULE}" = x"" ]; then
        modprobe ath10k_sdio
        sleep 15
    fi

    while [ ${COUNT} -lt 2 ]; do
        WLAN_RADIO_PATH="$(wifi status | jq -r .radio${COUNT}.config.path)"

        if [ x"${WLAN_RADIO_PATH}" = x"" ]; then
            break
        fi

        WLAN_RADIO_AUTOSTART="$(wifi status | jq -r .radio${COUNT}.autostart)"
        if [ x"${WLAN_RADIO_AUTOSTART}" != x"true" ]; then
            break
        fi

        WLAN_RADIO_DISABLED="$(wifi status | jq -r .radio${COUNT}.disabled)"

        if [ x"${WLAN_RADIO_DISABLED}" = x"true" ]; then
            break
        fi

        WLAN_RADIO_RETRY_FAILED="$(wifi status | jq -r .radio${COUNT}.retry_setup_failed)"

        if [ x"${WLAN_RADIO_RETRY_FAILED}" != x"true" ]; then
            break
        fi

        WLAN_RADIO_PENDING="$(wifi status | jq -r .radio${COUNT}.pending)"

        if [ x"${WLAN_RADIO_PENDING}" = x"true" ]; then
            break
        fi

        WLAN_RADIO_STATE="$(wifi status | jq -r .radio${COUNT}.up)"

        if [ x"${WLAN_RADIO_STATE}" = x"true" ]; then
            break
        fi

        wifi up radio${COUNT}

        COUNT=$(expr ${COUNT} + 1)
    done

    sleep 15
done

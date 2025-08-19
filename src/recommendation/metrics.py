#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

def init_metrics(meter):

    # Recommendations counter
    app_recommendations_counter = meter.create_counter(
        'app_recommendations_counter', unit='recommendations', description="Counts the total number of given recommendations"
    )

    # Cache metrics - track cache hits and misses for the in-memory cache
    app_cache_hits_counter = meter.create_counter(
        'app_cache_hits_counter', unit='hits', description="Counts the number of cache hits"
    )

    app_cache_misses_counter = meter.create_counter(
        'app_cache_misses_counter', unit='misses', description="Counts the number of cache misses"
    )

    rec_svc_metrics = {
        "app_recommendations_counter": app_recommendations_counter,
        "app_cache_hits_counter": app_cache_hits_counter,
        "app_cache_misses_counter": app_cache_misses_counter,
    }

    return rec_svc_metrics

package com.v2ray.ang.ui.main

/** Pick the lowest *successful* measured latency, preserving list order on ties. */
internal fun fastestTcpServer(
    testedGuids: List<String>,
    latency: (String) -> Long?,
): String? = testedGuids
    .mapNotNull { guid ->
        latency(guid)?.takeIf { it > 0L }?.let { guid to it }
    }
    .minByOrNull { it.second }
    ?.first

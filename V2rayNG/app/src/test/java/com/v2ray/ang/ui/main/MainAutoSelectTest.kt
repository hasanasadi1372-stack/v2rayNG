package com.v2ray.ang.ui.main

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class MainAutoSelectTest {
    @Test fun choosesLowestSuccessfulTcpDelay() {
        val latency = mapOf("slow" to 230L, "timeout" to -1L, "fast" to 41L, "untested" to 0L)
        assertEquals("fast", fastestTcpServer(latency.keys.toList(), latency::get))
    }

    @Test fun ignoresMissingAndFailedMeasurements() {
        val latency = mapOf("failed" to -1L, "zero" to 0L)
        assertNull(fastestTcpServer(listOf("failed", "missing", "zero"), latency::get))
        assertNull(fastestTcpServer(emptyList()) { 1L })
    }

    @Test fun tiesFollowTestListOrderAndUnlistedServersCannotWin() {
        val latency = mapOf("a" to 25L, "b" to 25L, "stale" to 1L)
        assertEquals("b", fastestTcpServer(listOf("b", "a"), latency::get))
    }
}

#!/usr/bin/env python3
"""Patch V2Prime Easy Connect after overlays: first subscription and selected deletion."""
from pathlib import Path
import re

ROOT = Path('V2rayNG/app/src/main/java/com/v2ray/ang/ui/main')
vm_path = ROOT / 'MainViewModel.kt'
activity_path = ROOT / 'MainActivity.kt'
if not vm_path.is_file() or not activity_path.is_file():
    raise SystemExit('V2Prime source files missing: patch must run after source overlays')
vm = vm_path.read_text(encoding='utf-8')
activity = activity_path.read_text(encoding='utf-8')

# Wait until new subscription groups/servers have actually loaded, including on first import.
a = vm.find('    private fun importBatchConfig(')
b = vm.find('    private fun importConfigViaSub(', a)
if a < 0 or b < 0:
    raise SystemExit('Cannot find batch subscription-import handler')
fragment = vm[a:b]
if 'V2PRIME_IMPORT_REFRESH_WAIT' not in fragment:
    needle = 'setupGroupTab(forceRefresh = true)'
    n = fragment.count(needle)
    if n < 2:
        raise SystemExit(f'Expected two import refresh branches, got {n}')
    fragment = fragment.replace(needle, 'setupGroupTab(forceRefresh = true).join() /* V2PRIME_IMPORT_REFRESH_WAIT */')
    vm = vm[:a] + fragment + vm[b:]

# All paths to refreshing the group list (including Subscription Settings) choose a valid
# initial server, without waiting for the app to restart.
needle = '''                val selectedServers = loadGroup(selectedGroup, forceRefresh)
                updateGroupUi(selectedGroup, selectedServers)'''
if 'V2PRIME_FIRST_IMPORT_SELECTION' not in vm:
    if vm.count(needle) != 1:
        raise SystemExit('Cannot locate group-load insertion point; upstream code changed')
    updated = '''                val selectedServers = loadGroup(selectedGroup, forceRefresh)
                // V2PRIME_FIRST_IMPORT_SELECTION: first sub needs no app restart.
                val storedSelection = dataSource.getSelectServer()
                if (storedSelection.isNullOrBlank() ||
                    dataSource.decodeServerConfig(storedSelection) == null
                ) {
                    val replacement = selectedServers.firstOrNull()?.guid
                        ?: groups.asSequence()
                            .flatMap { group -> dataSource.getServerGuidList(group.id).asSequence() }
                            .firstOrNull { guid -> dataSource.decodeServerConfig(guid) != null }
                    if (replacement != null) dataSource.setSelectServer(replacement)
                    _uiState.update { it.copy(selectedGuid = replacement) }
                }
                updateGroupUi(selectedGroup, selectedServers)'''
    vm = vm.replace(needle, updated, 1)

# The current code explicitly rejects deletion of selected profiles; remove that guard.
a = vm.find('    fun removeServerAndRefresh(guid: String) {')
b = vm.find('\n    fun ', a + 8)
if a < 0:
    raise SystemExit('Cannot find removeServerAndRefresh handler')
if b < 0:
    b = len(vm)
method = vm[a:b]
if 'V2PRIME_SELECTED_DELETE_ALLOWED' not in method:
    pattern = re.compile(
        r'        if \(guid == uiState\.value\.selectedGuid\) \{\s*'
        r'toast\(R\.string\.toast_action_not_allowed\)\s*return\s*\}\s*'
    )
    method, count = pattern.subn(
        '        // V2PRIME_SELECTED_DELETE_ALLOWED: confirmed removal is allowed.\n'
        '        if (guid.isBlank()) return\n', method, count=1
    )
    if count != 1:
        raise SystemExit('Selected-profile deletion guard has changed unexpectedly')
    needle = '            dataSource.removeServer(guid)\n'
    if method.count(needle) != 1:
        raise SystemExit('Cannot find profile storage deletion')
    method = method.replace(
        needle, needle +
        '            // MmkvManager clears the selected key when deleting that profile.\n'
        '            refreshSelectedGuid()\n', 1
    )
    vm = vm[:a] + method + vm[b:]

# A connected selected server must be stopped before its underlying config is deleted.
if 'V2PRIME_STOP_BEFORE_SELECTED_DELETE' not in activity:
    anchor = '                    is MainAction.SelectServer -> setSelectServer(action.guid)\n'
    if activity.count(anchor) != 1:
        raise SystemExit('Cannot find Activity SelectServer action handler')
    action = '''                    is MainAction.RemoveServer -> {
                        // V2PRIME_STOP_BEFORE_SELECTED_DELETE
                        val state = mainViewModel.uiState.value
                        if (state.isRunning && action.guid == state.selectedGuid) {
                            LauncherManager.stopService(this)
                        }
                        mainViewModel.onAction(action)
                    }
'''
    activity = activity.replace(anchor, anchor + action, 1)

assert all(tag in vm for tag in ('V2PRIME_IMPORT_REFRESH_WAIT', 'V2PRIME_FIRST_IMPORT_SELECTION', 'V2PRIME_SELECTED_DELETE_ALLOWED'))
assert 'V2PRIME_STOP_BEFORE_SELECTED_DELETE' in activity
vm_path.write_text(vm, encoding='utf-8')
activity_path.write_text(activity, encoding='utf-8')
print('V2Prime first-import and selected-config deletion patch applied successfully')

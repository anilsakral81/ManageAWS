#!/usr/bin/env python3
"""Test uptime tracking metrics"""

import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.metrics_service import MetricsService
from app.database import get_db


async def main():
    async for session in get_db():
        service = MetricsService(session)
        
        print('=== CURRENT STATE DURATION ===')
        current = await service.get_current_state_duration(6)
        print(f'State: {current["current_state"]}')
        print(f'Duration: {current["duration_formatted"]}')
        print(f'Since: {current["state_since"]}')
        print(f'Changed by: {current.get("changed_by", "N/A")}')
        print()
        
        print('=== MONTHLY METRICS (January 2026) ===')
        monthly = await service.get_monthly_uptime_downtime(6, 2026, 1)
        print(f'Uptime: {monthly["uptime_formatted"]} ({monthly["uptime_percentage"]:.2f}%)')
        print(f'Downtime: {monthly["downtime_formatted"]} ({monthly["downtime_percentage"]:.2f}%)')
        print(f'Total tracked: {monthly["uptime_percentage"] + monthly["downtime_percentage"]:.2f}%')
        print()
        
        print('=== STATE HISTORY (Last 5) ===')
        history = await service.get_state_history(6, limit=5)
        for i, record in enumerate(history["records"], 1):
            prev = record.get("previous_state", "None")
            print(f'{i}. {prev} -> {record["new_state"]} ({record["new_replicas"]} replicas)')
            print(f'   At: {record["changed_at"]} by {record.get("changed_by", "system")}')
            print(f'   Reason: {record.get("reason", "N/A")}')
        
        break


if __name__ == '__main__':
    asyncio.run(main())

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scanner
rows = scanner.close_watch()
for r in rows: print(r)
print("\n".join(scanner.close_watch_lines(rows)))

# Supervisor shift schedule, 28 Sep - 31 Oct 2026

`Supervisor_Shift_Schedule_Sep-Oct_2026.xlsx` has the roster, with two options:
fixed weekly offs and rotating weekly offs. The "Read me" sheet lists the rules.

To rebuild it (for example after changing a rule in `solver.py`):

    pip install ortools openpyxl
    python3 build_xlsx.py

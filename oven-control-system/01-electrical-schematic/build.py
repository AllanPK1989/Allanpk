import sys, os, glob, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "svg")
os.makedirs(OUT, exist_ok=True)

MODULES = ["sheets_a", "sheets_b", "sheets_c"]

def collect():
    fns = {}
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError:
            continue
        for name in dir(mod):
            if name.startswith("sheet") and name[5:].isdigit():
                fns[name] = getattr(mod, name)
    return [fns[k] for k in sorted(fns)]

def main():
    sheets = collect()
    paths = []
    for fn in sheets:
        s = fn()
        n = fn.__name__[5:]
        p = os.path.join(OUT, f"sheet-{n}.svg")
        s.save(p)
        paths.append(p)
        print("wrote", os.path.relpath(p, HERE))
    return paths

if __name__ == "__main__":
    main()

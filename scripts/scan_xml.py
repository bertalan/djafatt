"""Scan XML files in fatt2025 and show summary."""
import os
import re
import glob

for f in sorted(glob.glob("/Users/iberti/Coding/djafatt/fatt2025/*.xml")):
    with open(f) as fh:
        content = fh.read()
    num = re.search(r"<Numero>(.*?)</Numero>", content)
    data = re.search(r"<Data>(.*?)</Data>", content)
    tipo = re.search(r"<TipoDocumento>(.*?)</TipoDocumento>", content)
    tot = re.search(r"<ImportoTotaleDocumento>(.*?)</ImportoTotaleDocumento>", content)
    m = re.search(r"<CessionarioCommittente>.*?<Denominazione>(.*?)</Denominazione>", content, re.DOTALL)
    if not m:
        nome = re.search(r"<CessionarioCommittente>.*?<Nome>(.*?)</Nome>", content, re.DOTALL)
        cogn = re.search(r"<CessionarioCommittente>.*?<Cognome>(.*?)</Cognome>", content, re.DOTALL)
        client = ((nome.group(1) if nome else "") + " " + (cogn.group(1) if cogn else "")).strip()
    else:
        client = m.group(1)
    fname = os.path.basename(f)
    n = num.group(1) if num else "?"
    d = data.group(1) if data else "?"
    t = tipo.group(1) if tipo else "?"
    amount = tot.group(1) if tot else "?"
    print(f"{fname:30} #{n:4} {d:10} {t:5} {amount:>10}  {client[:40]}")

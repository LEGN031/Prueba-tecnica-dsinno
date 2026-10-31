import csv

def cargar_y_normalizar_csv(filepath):
    cuentas_procesadas = {}
    
    with open(filepath, mode='r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)  
        
        for idx, row in enumerate(reader, start=2):
            if not row or not row[0].strip():
                continue
                
            valor_raw = row[0].strip()
            
            if not valor_raw.isdigit():
                id_normalizado = valor_raw
                es_valido = False
            else:
                id_normalizado = str(int(valor_raw))
                es_valido = True
            
            if id_normalizado not in cuentas_procesadas:
                cuentas_procesadas[id_normalizado] = {
                    "es_valido": es_valido,
                    "veces_en_archivo": 1
                }
            else:
                cuentas_procesadas[id_normalizado]["veces_en_archivo"] += 1

    return cuentas_procesadas
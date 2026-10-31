from lectura import cargar_y_normalizar_csv
from state.estado import inicializar_bd 

if __name__ == "__main__":
    cuentas = cargar_y_normalizar_csv("cuentas.csv")
    

    invalidos = []
    validos = []
    for i in cuentas:
        if cuentas[i]['es_valido'] == True:
            validos.append(i)
        else:
            invalidos.append(i)      



    print(cuentas)
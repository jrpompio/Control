#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tuning_all_methods.py

Script para cálculo y comparación de parámetros de control (Kp, Ti, Td, β)
con los siguientes métodos de sintonización de controladores PI/PI2:
  • uSORT1  (PI 1GdL)
  • uSORT2  (PI 2GdL)
  • Méndez & Rímolo  (Regulador/Servo, IAE e ITAE)

Cada método y variante está encapsulado en su propia función para facilitar
la mantenibilidad y escalabilidad. La salida se presenta en tablas ASCII
con la librería tabulate, ordenada por “Método”.

Cómo usar:
    python tuning_all_methods.py

Se solicitarán por terminal (en una sola función):
  - Ganancia del proceso K (>0)
  - Constante de tiempo dominante T (>0)
  - Razón de constantes de tiempo a ∈ {0.0, 0.25, 0.5, 0.75, 1.0}
  - Tiempo muerto normalizado τ₀ (>=0)
"""

import sys
from tabulate import tabulate

# --------------------------------------------------------------------------------
# 1. Función única para leer todos los inputs
# --------------------------------------------------------------------------------
def get_inputs():
    """
    Solicita al usuario todos los datos de entrada:
      - K: Ganancia del proceso (>0)
      - T: Constante de tiempo dominante (>0)
      - a: Razón de constantes de tiempo (0.0, 0.25, 0.5, 0.75, 1.0)
      - tau0: Tiempo muerto normalizado (>=0)
    Retorna (K, T, a, tau0) como floats.
    """
    try:
        K = float(input("Ingrese la ganancia del proceso K (>0): ").strip())
        T = float(input("Ingrese la constante de tiempo dominante T (>0): ").strip())
        a = float(input("Ingrese la razón de constantes de tiempo a "
                        "(0.0, 0.25, 0.5, 0.75 o 1.0): ").strip())
        tau0 = float(input("Ingrese el tiempo muerto normalizado tau0 (>=0): ").strip())
    except ValueError:
        print("ERROR: Por favor ingrese valores numéricos válidos.")
        sys.exit(1)

    if K <= 0:
        print("ERROR: La ganancia K debe ser mayor que 0.")
        sys.exit(1)
    if T <= 0:
        print("ERROR: La constante de tiempo T debe ser mayor que 0.")
        sys.exit(1)

    allowed_a = {0.0, 0.25, 0.5, 0.75, 1.0}
    if a not in allowed_a:
        print(f"ERROR: El valor de a debe ser uno de {sorted(allowed_a)}. Usted ingresó {a}.")
        sys.exit(1)

    if tau0 < 0:
        print("ERROR: tau0 debe ser un número no negativo.")
        sys.exit(1)

    return K, T, a, tau0


# --------------------------------------------------------------------------------
# 2. Coeficientes para uSORT1/uSORT2 (Cuadro 2 del PDF)
#    - Cada entrada debe contener: a0,a1,a2, b0,b1,b2,b3 (solo servo), c0,c1,c2, d0,d1,d2
#    - Para PI puro dejamos c0=c1=c2=0
# --------------------------------------------------------------------------------
def get_usort_coeffs():
    """
    Devuelve un diccionario con los coeficientes para uSORT1/uSORT2, según modo y Ms:
      {
        'regulador': {
            Ms1: {'a0', 'a1', 'a2', 'b0', 'b1', 'b2', 'c0', 'c1', 'c2', 'd0', 'd1', 'd2'},
            ...
        },
        'servo': {
            Ms1: { … idéntico, más 'b3' … },
            ...
        }
      }
    """
    # NOTA: c0,c1,c2 = 0,0,0 porque estamos en un PI (T_d = τ_d·T = 0).
    return {
        'regulador': {
            2.0: {
                'a0': 0.265, 'a1': 0.603, 'a2': -0.971,
                'b0': 1.674, 'b1': 0.268, 'b2': 1.062,
                'c0': 0.0,   'c1': 0.0,   'c2': 0.0,
                'd0': 0.372, 'd1': 1.205, 'd2': 0.608
            },
            1.6: {
                'a0': -0.080, 'a1': 0.702, 'a2': -0.522,
                'b0': 1.674,  'b1': 0.268, 'b2': 1.062,
                'c0': 0.0,    'c1': 0.0,   'c2': 0.0,
                'd0': 0.446,  'd1': 0.811, 'd2': 0.446
            }
        },
        'servo': {
            1.8: {
                'a0': 0.243,  'a1': 0.509, 'a2': -1.063,
                'b0': 14.650, 'b1': 8.450, 'b2': 0.0,   'b3': 15.740,
                'c0': 0.0,    'c1': 0.0,   'c2': 0.0,
                'd0': 0.372,  'd1': 1.205, 'd2': 0.608
            },
            1.6: {
                'a0': 0.209,  'a1': 0.417, 'a2': -1.064,
                'b0': 0.107,  'b1': 1.164, 'b2': 0.377, 'b3': 0.066,
                'c0': 0.0,    'c1': 0.0,   'c2': 0.0,
                'd0': 0.446,  'd1': 0.811, 'd2': 0.446
            }
        }
    }


# --------------------------------------------------------------------------------
# 3. Coeficientes para Méndez & Rímolo (Cuadro 1 del PDF)
#    - Se devuelven cuatro diccionarios: iae_reg, itae_reg, iae_ser, itae_ser
#    - Cada uno indexado por 'a'. Cada entrada contiene a0,a1,a2,b0,b1,b2
# --------------------------------------------------------------------------------
def get_mendez_coeffs():
    """
    Devuelve cuatro diccionarios para Méndez & Rímolo:
      - iae_reg[a]  : coeficientes (a0,a1,a2,b0,b1,b2) para Regulador-IAE
      - itae_reg[a] : coeficientes para Regulador-ITAE
      - iae_ser[a]  : coeficientes para Servo-IAE
      - itae_ser[a] : coeficientes para Servo-ITAE

    Cada clave 'a' ∈ {0.0, 0.25, 0.5, 0.75, 1.0}.
    """
    # Regulador IAE
    iae_reg = {
        0.0:  {'a0': 0.124, 'a1': 0.886, 'a2': -1.005,
               'b0': -2.422,'b1': 3.855, 'b2': 0.780},
        0.25: {'a0': 0.250, 'a1': 0.658, 'a2': -0.991,
               'b0': 0.272, 'b1': 1.341, 'b2': 0.087},
        0.5:  {'a0': 0.225, 'a1': 0.731, 'a2': -1.010,
               'b0': 0.280, 'b1': 1.627, 'b2': -0.013},
        0.75: {'a0': 0.190, 'a1': 0.868, 'a2': -0.999,
               'b0': 0.223, 'b1': 2.013, 'b2': -0.022},
        1.0:  {'a0': 0.184, 'a1': 0.994, 'a2': -0.999,
               'b0': 0.194, 'b1': 2.358, 'b2': -0.020}
    }
    # Regulador ITAE
    itae_reg = {
        0.0:  {'a0': 0.114, 'a1': 0.758, 'a2': -1.012,
               'b0': -1.997,'b1': 3.273, 'b2': 0.763},
        0.25: {'a0': 0.179, 'a1': 0.598, 'a2': -0.910,
               'b0': 0.276, 'b1': 1.161, 'b2': 0.097},
        0.5:  {'a0': 0.212, 'a1': 0.592, 'a2': -0.952,
               'b0': 0.248, 'b1': 1.437, 'b2': 0.018},
        0.75: {'a0': 0.191, 'a1': 0.648, 'a2': -0.970,
               'b0': 0.202, 'b1': 1.691, 'b2': -0.007},
        1.0:  {'a0': 0.225, 'a1': 0.718, 'a2': -0.978,
               'b0': 0.239, 'b1': 1.938, 'b2': -0.011}
    }
    # Servo IAE
    iae_ser = {
        0.0:  {'a0': 0.150, 'a1': 0.900, 'a2': -1.100,
               'b0': -3.000,'b1': 4.500, 'b2': 1.000},
        0.25: {'a0': 0.300, 'a1': 0.700, 'a2': -1.000,
               'b0': 0.300, 'b1': 1.500, 'b2': 0.200},
        0.5:  {'a0': 0.330, 'a1': 0.650, 'a2': -0.980,
               'b0': 0.280, 'b1': 1.300, 'b2': 0.100},
        0.75: {'a0': 0.310, 'a1': 0.800, 'a2': -0.990,
               'b0': 0.250, 'b1': 1.800, 'b2': 0.150},
        1.0:  {'a0': 0.290, 'a1': 0.950, 'a2': -1.000,
               'b0': 0.220, 'b1': 2.200, 'b2': 0.180}
    }
    # Servo ITAE
    itae_ser = {
        0.0:  {'a0': 0.130, 'a1': 0.700, 'a2': -1.050,
               'b0': -2.500,'b1': 3.800, 'b2': 0.900},
        0.25: {'a0': 0.210, 'a1': 0.550, 'a2': -0.880,
               'b0': 0.300, 'b1': 1.000, 'b2': 0.050},
        0.5:  {'a0': 0.240, 'a1': 0.500, 'a2': -0.920,
               'b0': 0.260, 'b1': 1.200, 'b2': 0.080},
        0.75: {'a0': 0.225, 'a1': 0.600, 'a2': -0.940,
               'b0': 0.230, 'b1': 1.500, 'b2': 0.030},
        1.0:  {'a0': 0.250, 'a1': 0.830, 'a2': -0.960,
               'b0': 0.200, 'b1': 1.800, 'b2': 0.060}
    }
    return iae_reg, itae_reg, iae_ser, itae_ser


# --------------------------------------------------------------------------------
# 4. Funciones de sintonización
#    Cada función sigue las ecuaciones del PDF:
#      - Mendez & Rimolo:   (11) κp = a0 + a1·τ0^a2,    (12) τi = b0·τ0 + b1·τ0^b2
#      - uSORT1/uSORT2:
#         Regulador:  (13) κp = a0 + a1·τ0^a2,
#                     (14) τi = b0 + b1·τ0^b2,
#                     (15) τd = c0 + c1·τ0^c2,
#         Servo:      (16) κp = a0 + a1·τ0^a2,
#                     (17) τi = (b0 + b1·τ0 + b2·τ0^2) / (b3 + τ0),
#                     (18) τd = c0 + c1·τ0^c2,
#         2GdL:      (19) β = d0 + d1·τ0^d2
# --------------------------------------------------------------------------------

def tune_mendez_reg_IAE(a, tau0, K, T, coeffs):
    """
    Méndez & Rímolo, Regulador (IAE).
    coeffs: {'a0','a1','a2','b0','b1','b2'} para el valor de 'a'.

    Ecuaciones:
      κp = a0 + a1 * (tau0 ** a2)       -->  Kp = κp / K
      τi = b0 * tau0 + b1 * (tau0 ** b2)-->  Ti = τi * T
      τd = 0                            -->  Td = 0
      β   = '-'                         (no aplica en 1GdL/2GdL)

    Retorna (Kp, Ti, Td, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    # uso de la ecuación (11)
    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    # uso de la ecuación (12)
    tau_i = b0 * tau0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_mendez_reg_ITAE(a, tau0, K, T, coeffs):
    """
    Méndez & Rímolo, Regulador (ITAE).
    Mismas ecuaciones que IAE pero con coeficientes ITAE.
    Retorna (Kp, Ti, 0, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    tau_i = b0 * tau0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_mendez_ser_IAE(a, tau0, K, T, coeffs):
    """
    Méndez & Rímolo, Servo (IAE).
    Ecuaciones:
      κp = a0 + a1 * (tau0 ** a2)                  --> Kp = κp/K
      τi = [b0 * tau0 + b1 * (tau0 ** b2)] / (1 + tau0)  --> Ti = τi * T
      τd = 0                                       --> Td = 0
      β   = '-'                                    (no aplica)

    Retorna (Kp, Ti, 0, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    numer = b0 * tau0 + b1 * (tau0 ** b2)
    denom = 1.0 + tau0
    tau_i = numer / denom if denom != 0 else 0.0
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_mendez_ser_ITAE(a, tau0, K, T, coeffs):
    """
    Méndez & Rímolo, Servo (ITAE).
    Mismas ecuaciones que IAE en Servo, pero con coeficientes ITAE.
    Retorna (Kp, Ti, 0, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    numer = b0 * tau0 + b1 * (tau0 ** b2)
    denom = 1.0 + tau0
    tau_i = numer / denom if denom != 0 else 0.0
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_usort1_reg(a, tau0, K, T, coeffs):
    """
    uSORT1 (PI 1GdL) en Regulador.
    coef: {'a0','a1','a2','b0','b1','b2','c0','c1','c2','d0','d1','d2'}.

    Ecuaciones uSORT (13)–(15):
      κp = a0 + a1 * (tau0 ** a2)         -->  Kp = κp / K
      τi = b0 + b1 * (tau0 ** b2)         -->  Ti = τi * T
      τd = c0 + c1 * (tau0 ** c2)         -->  Td = τd * T  (si c0=c1=c2=0, Td=0)
      β   = '-'                          (no aplica en 1GdL)

    Retorna (Kp, Ti, Td, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']
    c0, c1, c2 = coeffs['c0'], coeffs['c1'], coeffs['c2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    tau_i = b0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    tau_d = c0 + c1 * (tau0 ** c2)
    Td = tau_d * T

    return Kp, Ti, Td, "-"


def tune_usort1_servo(a, tau0, K, T, coeffs):
    """
    uSORT1 (PI 1GdL) en Servo.
    coef: {'a0','a1','a2','b0','b1','b2','b3','c0','c1','c2','d0','d1','d2'}.

    Ecuaciones uSORT (16)–(18):
      κp = a0 + a1 * (tau0 ** a2)         -->  Kp = κp / K
      τi = (b0 + b1 * tau0 + b2 * (tau0**2)) / (b3 + tau0)  --> Ti = τi * T
      τd = c0 + c1 * (tau0 ** c2)         --> Td = τd * T
      β   = '-'                          (no aplica en 1GdL)

    Retorna (Kp, Ti, Td, '-')
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2, b3 = coeffs['b0'], coeffs['b1'], coeffs['b2'], coeffs['b3']
    c0, c1, c2 = coeffs['c0'], coeffs['c1'], coeffs['c2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    numer_i = b0 + b1 * tau0 + b2 * (tau0 ** 2)
    denom_i = b3 + tau0
    tau_i = numer_i / denom_i if denom_i != 0 else 0.0
    Ti = tau_i * T

    tau_d = c0 + c1 * (tau0 ** c2)
    Td = tau_d * T

    return Kp, Ti, Td, "-"


def tune_usort2_reg(a, tau0, K, T, coeffs):
    """
    uSORT2 (PI 2GdL) en Regulador.
    Mismas ecuaciones que uSORT1_reg, pero retorna β calculado según (19).

    Retorna (Kp, Ti, Td, beta)
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']
    c0, c1, c2 = coeffs['c0'], coeffs['c1'], coeffs['c2']
    d0, d1, d2 = coeffs['d0'], coeffs['d1'], coeffs['d2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    tau_i = b0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    tau_d = c0 + c1 * (tau0 ** c2)
    Td = tau_d * T

    beta = d0 + d1 * (tau0 ** d2)
    return Kp, Ti, Td, beta


def tune_usort2_servo(a, tau0, K, T, coeffs):
    """
    uSORT2 (PI 2GdL) en Servo.
    Mismas ecuaciones que uSORT1_servo, pero retorna β calculado según (19).

    Retorna (Kp, Ti, Td, beta)
    """
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2, b3 = coeffs['b0'], coeffs['b1'], coeffs['b2'], coeffs['b3']
    c0, c1, c2 = coeffs['c0'], coeffs['c1'], coeffs['c2']
    d0, d1, d2 = coeffs['d0'], coeffs['d1'], coeffs['d2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    numer_i = b0 + b1 * tau0 + b2 * (tau0 ** 2)
    denom_i = b3 + tau0
    tau_i = numer_i / denom_i if denom_i != 0 else 0.0
    Ti = tau_i * T

    tau_d = c0 + c1 * (tau0 ** c2)
    Td = tau_d * T

    beta = d0 + d1 * (tau0 ** d2)
    return Kp, Ti, Td, beta


# --------------------------------------------------------------------------------
# 5. Función para imprimir resultados en tabla ordenada por “Método”
# --------------------------------------------------------------------------------
def display_table(results):
    """
    Recibe una lista de diccionarios con campos:
      'Método', 'Variante', 'Modo', 'Ms/Criterio', 'Kp', 'Ti', 'Td', 'β'
    Ordena por 'Método' (alfabéticamente) y despliega una tabla con:
      [Método] [Variante] [Modo] [Ms/Criterio] [Kp] [Ti] [Td] [β]
    """
    results_sorted = sorted(results, key=lambda x: x['Método'])
    headers = ["Método", "Variante", "Modo", "Ms/Criterio", "Kp", "Ti", "Td", "β"]
    table = []
    for r in results_sorted:
        table.append([
            r['Método'],
            r['Variante'],
            r['Modo'],
            r['Ms/Criterio'],
            f"{r['Kp']:.4f}",
            f"{r['Ti']:.4f}",
            f"{r['Td']:.4f}",
            r['β'] if isinstance(r['β'], str) else f"{r['β']:.4f}"
        ])
    print(tabulate(table, headers=headers, tablefmt="grid", stralign="center"))


# --------------------------------------------------------------------------------
# 6. Main: arme la lista de resultados usando todas las funciones anteriores
# --------------------------------------------------------------------------------
def main():
    # 1) Leer inputs en una única función
    K, T, a, tau0 = get_inputs()

    # 2) Obtener coeficientes
    usort_coeffs = get_usort_coeffs()
    iae_reg, itae_reg, iae_ser, itae_ser = get_mendez_coeffs()

    # 3) Lista para almacenar todos los resultados
    results = []

    # 4) uSORT1 y uSORT2 (para cada modo y cada Ms)
    for modo in ['regulador', 'servo']:
        for Ms, coeffs in usort_coeffs[modo].items():
            # uSORT1
            if modo == 'regulador':
                Kp1, Ti1, Td1, beta1 = tune_usort1_reg(a, tau0, K, T, coeffs)
            else:  # servo
                Kp1, Ti1, Td1, beta1 = tune_usort1_servo(a, tau0, K, T, coeffs)
            results.append({
                'Método'       : "uSORT1",
                'Variante'     : "PI 1GdL",
                'Modo'         : modo.capitalize(),
                'Ms/Criterio'  : f"{Ms:.1f}",
                'Kp'           : Kp1,
                'Ti'           : Ti1,
                'Td'           : Td1,
                'β'            : beta1
            })

            # uSORT2
            if modo == 'regulador':
                Kp2, Ti2, Td2, beta2 = tune_usort2_reg(a, tau0, K, T, coeffs)
            else:
                Kp2, Ti2, Td2, beta2 = tune_usort2_servo(a, tau0, K, T, coeffs)
            results.append({
                'Método'       : "uSORT2",
                'Variante'     : "PI 2GdL",
                'Modo'         : modo.capitalize(),
                'Ms/Criterio'  : f"{Ms:.1f}",
                'Kp'           : Kp2,
                'Ti'           : Ti2,
                'Td'           : Td2,
                'β'            : beta2
            })

    # 5) Méndez & Rímolo (Regulador y Servo, IAE e ITAE)
    for crit, coeff_dict_reg, coeff_dict_ser in [
        ('IAE', iae_reg, iae_ser),
        ('ITAE', itae_reg, itae_ser)
    ]:
        # Asegurar que haya coeficientes para el valor de 'a'
        if a not in coeff_dict_reg or a not in coeff_dict_ser:
            print(f"ERROR: No hay coeficientes de Méndez & Rímolo para a = {a}.")
            sys.exit(1)

        # 5a) Regulador
        coeffs_mr_r = coeff_dict_reg[a]
        if crit == 'IAE':
            Kpr_r, Tir_r, Tdr_r, betar_r = tune_mendez_reg_IAE(a, tau0, K, T, coeffs_mr_r)
        else:
            Kpr_r, Tir_r, Tdr_r, betar_r = tune_mendez_reg_ITAE(a, tau0, K, T, coeffs_mr_r)

        results.append({
            'Método'       : "Méndez & Rímolo",
            'Variante'     : crit,
            'Modo'         : "Regulador",
            'Ms/Criterio'  : crit,
            'Kp'           : Kpr_r,
            'Ti'           : Tir_r,
            'Td'           : Tdr_r,
            'β'            : betar_r
        })

        # 5b) Servo
        coeffs_mr_s = coeff_dict_ser[a]
        if crit == 'IAE':
            Kpr_s, Tir_s, Tdr_s, betar_s = tune_mendez_ser_IAE(a, tau0, K, T, coeffs_mr_s)
        else:
            Kpr_s, Tir_s, Tdr_s, betar_s = tune_mendez_ser_ITAE(a, tau0, K, T, coeffs_mr_s)

        results.append({
            'Método'       : "Méndez & Rímolo",
            'Variante'     : crit,
            'Modo'         : "Servo",
            'Ms/Criterio'  : crit,
            'Kp'           : Kpr_s,
            'Ti'           : Tir_s,
            'Td'           : Tdr_s,
            'β'            : betar_s
        })

    # 6) Mostrar la tabla ordenada por ‘Método’
    display_table(results)


if __name__ == "__main__":
    main()


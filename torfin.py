#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tuning_all_methods.py

Script para cálculo y comparación de parámetros de control (Kp, Ti, Td, β)
con los siguientes métodos de sintonización de controladores PI/PI2/PID:
  • uSORT1   (PI 1GdL / PID 1GdL)
  • uSORT2   (PI 2GdL / PID 2GdL)
  • Méndez & Rímolo   (Regulador/Servo, IAE e ITAE, solo PI)
  • López et al.      (P, PI, PID – Regulador – ISE, IAE, ITAE)
  • Rovira et al.     (PI, PID – Servo – IAE, ITAE)

Uso (por terminal):
    python tuning_all_methods.py K T a tau0

  - K     : Ganancia del proceso (float > 0)
  - T     : Constante de tiempo dominante (float > 0)
  - a     : Razón de constantes de tiempo (0.0, 0.25, 0.5, 0.75, 1.0)
  - tau0  : Tiempo muerto normalizado (float >= 0)

Si no se reciben exactamente 4 argumentos o alguno es inválido, se muestra esta ayuda.
"""

import sys
from tabulate import tabulate

# --------------------------------------------------------------------------------
# 1. Función para procesar argumentos de terminal
# --------------------------------------------------------------------------------
def parse_args():
    """
    Verifica que se hayan recibido exactamente 4 argumentos (aparte del nombre del script):
      K, T, a, tau0
    Si no, muestra la ayuda y termina.
    Si sí, los convierte a float y valida:
      - K > 0
      - T > 0
      - a en {0.0, 0.25, 0.5, 0.75, 1.0}
      - tau0 >= 0
    Retorna (K, T, a, tau0) si todo es correcto. En caso contrario, imprime la ayuda y sale.
    """
    usage = (
        "\nUso:\n"
        "  python tuning_all_methods.py K T a tau0\n\n"
        "  - K    : Ganancia del proceso (float > 0)\n"
        "  - T    : Constante de tiempo dominante (float > 0)\n"
        "  - a    : Razón de constantes de tiempo (0.0, 0.25, 0.5, 0.75, 1.0)\n"
        "  - tau0 : Tiempo muerto normalizado (float >= 0)\n"
    )

    if len(sys.argv) != 5:
        print("ERROR: Número incorrecto de argumentos." + usage)
        sys.exit(1)

    try:
        K = float(sys.argv[1])
        T = float(sys.argv[2])
        a = float(sys.argv[3])
        tau0 = float(sys.argv[4])
    except ValueError:
        print("ERROR: Todos los argumentos deben ser números válidos." + usage)
        sys.exit(1)

    if K <= 0 or T <= 0:
        print("ERROR: K y T deben ser mayores que 0." + usage)
        sys.exit(1)

    allowed_a = {0.0, 0.25, 0.5, 0.75, 1.0}
    if a not in allowed_a:
        print(f"ERROR: El valor de a debe ser uno de {sorted(allowed_a)}. Usted ingresó {a}." + usage)
        sys.exit(1)

    if tau0 < 0:
        print("ERROR: tau0 debe ser un número no negativo." + usage)
        sys.exit(1)

    return K, T, a, tau0


# --------------------------------------------------------------------------------
# 2. Coeficientes para uSORT1/uSORT2 (Cuadro 2 del PDF)
#    Con valores CORRECTOS para PI y PID.
# --------------------------------------------------------------------------------
def get_usort_coeffs():
    """
    Devuelve un diccionario anidado con los coeficientes para uSORT1/uSORT2,
    según modo (regulador/servo), tipo de controlador (PI/PID) y nivel de Ms:
      {
        'regulador': {
            'PI':  { Ms: { a0,a1,a2, b0,b1,b2, c0,c1,c2, d0,d1,d2 }, ... },
            'PID': { Ms: { a0,a1,a2, b0,b1,b2, c0,c1,c2, d0,d1,d2 }, ... }
        },
        'servo': {
            'PI':  { Ms: { a0,a1,a2, b0,b1,b2,b3, c0,c1,c2, d0,d1,d2 }, ... },
            'PID': { Ms: { a0,a1,a2, b0,b1,b2,b3, c0,c1,c2, d0,d1,d2 }, ... }
        }
      }
    """
    return {
        'regulador': {
            'PI': {
                # Robustez Ms = 2.0
                2.0: {
                    'a0': 0.265,  'a1': 0.603,  'a2': -0.971,
                    'b0': -1.382, 'b1':  2.837, 'b2':  0.211,
                    'c0': 0.0,    'c1':  0.0,   'c2':  0.0,
                    'd0': 0.372,  'd1':  1.205, 'd2':  0.608
                },
                # Robustez Ms = 1.6
                1.6: {
                    'a0': 0.175,  'a1': 0.466,  'a2': -0.911,
                    'b0': -1.382, 'b1':  2.837, 'b2':  0.211,
                    'c0': 0.0,    'c1':  0.0,   'c2':  0.0,
                    'd0': 0.446,  'd1':  0.811, 'd2':  0.446
                }
            },
            'PID': {
                # Robustez Ms = 2.0  (valores EXACTOS para PID Regulador)
                2.0: {
                    'a0': 0.235,  'a1': 0.840,  'a2': -0.919,
                    'b0': -0.198, 'b1': 1.291,  'b2':  0.485,
                    'c0':  0.004, 'c1': 0.389,  'c2':  0.869,
                    'd0':  0.248, 'd1': 0.571,  'd2':  0.362
                },
                # Robustez Ms = 1.6  (valores EXACTOS para PID Regulador)
                1.6: {
                    'a0': 0.435,  'a1': 0.551,  'a2': -1.123,
                    'b0': 0.095,  'b1': 1.165,  'b2':  0.517,
                    'c0': 0.104,  'c1': 0.414,  'c2':  0.758,
                    'd0': 0.255,  'd1': 0.277,  'd2':  0.476
                }
            }
        },
        'servo': {
            'PI': {
                # Robustez Ms = 1.8
                1.8: {
                    'a0':  0.243, 'a1':  0.509, 'a2': -1.063,
                    'b0': 14.650, 'b1':  8.450, 'b2':  0.000, 'b3': 15.740,
                    'c0':  0.0,   'c1':  0.0,   'c2':  0.0,
                    'd0':  0.372, 'd1':  1.205, 'd2':  0.608
                },
                # Robustez Ms = 1.6
                1.6: {
                    'a0':  0.209, 'a1':  0.417, 'a2': -1.064,
                    'b0':  0.107, 'b1':  1.164, 'b2':  0.377, 'b3':  0.066,
                    'c0':  0.0,   'c1':  0.0,   'c2':  0.0,
                    'd0':  0.446, 'd1':  0.811, 'd2':  0.446
                }
            },
            'PID': {
                # Robustez Ms = 1.8 (valores EXACTOS para PID Servo)
                1.8: {
                    'a0':  0.377,  'a1':  0.727,  'a2': -1.041,
                    'b0':  1.687,  'b1': 339.2,  'b2': 39.86, 'b3': 1299.0,
                    'c0': -0.016,  'c1':  0.333,  'c2':  0.815,
                    'd0':  0.248,  'd1':  0.571,  'd2':  0.362
                },
                # Robustez Ms = 1.6 (valores EXACTOS para PID Servo)
                1.6: {
                    'a0':  0.502,  'a1':  0.518,  'a2': -1.194,
                    'b0':  0.135,  'b1':  1.355,  'b2':  0.333, 'b3':  0.403,
                    'c0':  0.026,  'c1':  0.403,  'c2':  0.613,
                    'd0':  0.255,  'd1':  0.277,  'd2':  0.476
                }
            }
        }
    }


# --------------------------------------------------------------------------------
# 3. Coeficientes para Méndez & Rímolo (Cuadro 1 del PDF)
#    Ahora con los valores CORRECTOS SOLO PI.
# --------------------------------------------------------------------------------
def get_mendez_coeffs():
    """
    Devuelve cuatro diccionarios para Méndez & Rímolo:
      - iae_reg[a]  : coeficientes (a0,a1,a2,b0,b1,b2) para Regulador-IAE (PI)
      - itae_reg[a] : coeficientes para Regulador-ITAE (PI)
      - iae_ser[a]  : coeficientes para Servo-IAE (PI)
      - itae_ser[a] : coeficientes para Servo-ITAE (PI)

    Cada clave 'a' ∈ {0.0, 0.25, 0.50, 0.75, 1.0}.
    """
    # Regulador IAE
    iae_reg = {
        0.0:  {'a0': 0.124, 'a1': 0.886, 'a2': -1.005,
               'b0': -2.422, 'b1': 3.855, 'b2': 0.780},
        0.25: {'a0': 0.250, 'a1': 0.658, 'a2': -0.991,
               'b0':  0.272, 'b1': 1.341, 'b2': 0.087},
        0.5:  {'a0': 0.225, 'a1': 0.731, 'a2': -1.010,
               'b0':  0.280, 'b1': 1.627, 'b2': -0.013},
        0.75: {'a0': 0.190, 'a1': 0.868, 'a2': -0.999,
               'b0':  0.223, 'b1': 2.013, 'b2': -0.022},
        1.0:  {'a0': 0.184, 'a1': 0.994, 'a2': -0.999,
               'b0':  0.194, 'b1': 2.358, 'b2': -0.020}
    }

    # Regulador ITAE
    itae_reg = {
        0.0:  {'a0': 0.114, 'a1': 0.758, 'a2': -1.012,
               'b0': -1.997, 'b1': 3.273, 'b2': 0.763},
        0.25: {'a0': 0.179, 'a1': 0.598, 'a2': -0.910,
               'b0':  0.276, 'b1': 1.161, 'b2': 0.097},
        0.5:  {'a0': 0.212, 'a1': 0.592, 'a2': -0.952,
               'b0':  0.248, 'b1': 1.437, 'b2': 0.018},
        0.75: {'a0': 0.191, 'a1': 0.648, 'a2': -0.970,
               'b0':  0.202, 'b1': 1.691, 'b2': -0.007},
        1.0:  {'a0': 0.225, 'a1': 0.718, 'a2': -0.978,
               'b0':  0.239, 'b1': 1.938, 'b2': -0.011}
    }

    # Servo IAE
    iae_ser = {
        0.0:  {'a0': 0.265,  'a1': 0.509, 'a2': -1.042,
               'b0': 0.433,  'b1': 0.922, 'b2': -0.017},
        0.25: {'a0': -0.035, 'a1': 0.761, 'a2': -0.619,
               'b0': 0.395,  'b1': 1.117, 'b2': -0.080},
        0.5:  {'a0': 0.013,  'a1': 0.730, 'a2': -0.616,
               'b0': 0.382,  'b1': 1.381, 'b2': -0.114},
        0.75: {'a0': -0.040, 'a1': 0.835, 'a2': -0.587,
               'b0': 0.353,  'b1': 1.671, 'b2': -0.121},
        1.0:  {'a0': 0.035,  'a1': 0.825, 'a2': -0.618,
               'b0': 0.406,  'b1': 1.903, 'b2': -0.134}
    }

    # Servo ITAE
    itae_ser = {
        0.0:  {'a0': 0.209,  'a1': 0.441, 'a2': -1.054,
               'b0': 0.326,  'b1': 0.882, 'b2': -0.035},
        0.25: {'a0': -0.148, 'a1': 0.748, 'a2': -0.475,
               'b0': 0.316,  'b1': 1.005, 'b2': -0.033},
        0.5:  {'a0': -0.198, 'a1': 0.788, 'a2': -0.416,
               'b0': 0.307,  'b1': 1.169, 'b2': -0.067},
        0.75: {'a0': -0.299, 'a1': 0.914, 'a2': -0.372,
               'b0': 0.299,  'b1': 1.371, 'b2': -0.076},
        1.0:  {'a0': -0.338, 'a1': 0.997, 'a2': -0.360,
               'b0': 0.291,  'b1': 1.605, 'b2': -0.072}
    }

    return iae_reg, itae_reg, iae_ser, itae_ser


# --------------------------------------------------------------------------------
# 4. Coeficientes para López et al. (1967) y Rovira et al. (1969)
# --------------------------------------------------------------------------------
def get_lopez_coeffs():
    return {
        'P': {
            'ISE':  {'a': 1.4110, 'b': -0.9170},
            'IAE':  {'a': 0.9023, 'b': -0.9850},
            'ITAE': {'a': 0.4897, 'b': -1.0850}
        },
        'PI': {
            'ISE':  {'a': 1.3050, 'b': -0.9600, 'c': 2.0325, 'd': 0.7390},
            'IAE':  {'a': 0.9840, 'b': -0.9860, 'c': 1.6447, 'd': 0.7070},
            'ITAE': {'a': 0.8590, 'b': -0.9770, 'c': 1.4837, 'd': 0.6800}
        },
        'PID': {
            'ISE':  {'a': 1.4950, 'b': -0.9450, 'c': 0.9083, 'd': 0.7710, 'e': 0.5600, 'f': 1.0060},
            'IAE':  {'a': 1.4350, 'b': -0.9210, 'c': 1.1390, 'd': 0.7490, 'e': 0.4820, 'f': 1.1370},
            'ITAE': {'a': 1.3570, 'b': -0.9470, 'c': 1.1876, 'd': 0.7380, 'e': 0.3810, 'f': 0.9950}
        }
    }


def get_rovira_coeffs():
    return {
        'PI': {
            'IAE':  {'a': 0.7580, 'b': -0.8610, 'c': 1.0200, 'd': -0.3230},
            'ITAE': {'a': 0.5860, 'b': -0.9160, 'c': 1.0300, 'd': -0.1650}
        },
        'PID': {
            'IAE':  {'a': 1.0860, 'b': -0.8690, 'c': 0.7400, 'd': -0.1300, 'e': 0.3480, 'f': 0.9140},
            'ITAE': {'a': 0.9650, 'b': -0.8500, 'c': 0.7960, 'd': -0.1465, 'e': 0.3080, 'f': 0.9290}
        }
    }


# --------------------------------------------------------------------------------
# 5. Funciones de sintonización (Méndez & Rímolo, uSORT1, uSORT2)
# --------------------------------------------------------------------------------
def tune_mendez_reg_IAE(a, tau0, K, T, coeffs):
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    tau_i = b0 * tau0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_mendez_reg_ITAE(a, tau0, K, T, coeffs):
    a0, a1, a2 = coeffs['a0'], coeffs['a1'], coeffs['a2']
    b0, b1, b2 = coeffs['b0'], coeffs['b1'], coeffs['b2']

    kappa_p = a0 + a1 * (tau0 ** a2)
    Kp = kappa_p / K

    tau_i = b0 * tau0 + b1 * (tau0 ** b2)
    Ti = tau_i * T

    Td = 0.0
    return Kp, Ti, Td, "-"


def tune_mendez_ser_IAE(a, tau0, K, T, coeffs):
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
# 6. Funciones de sintonización para López et al. (1967)
# --------------------------------------------------------------------------------
def tune_lopez_P(tau0, K, params):
    a = params['a']
    b = params['b']
    kpk = a * (tau0 ** b)
    Kp = kpk / K
    return Kp, 0.0, 0.0, "-"


def tune_lopez_PI(tau0, K, T, params):
    a = params['a']
    b = params['b']
    c = params['c']
    d = params['d']

    kpk = a * (tau0 ** b)
    Kp = kpk / K

    tau_i = c * (tau0 ** d)
    Ti = tau_i * T

    return Kp, Ti, 0.0, "-"


def tune_lopez_PID(tau0, K, T, params):
    a = params['a']
    b = params['b']
    c = params['c']
    d = params['d']
    e = params['e']
    f = params['f']

    kpk = a * (tau0 ** b)
    Kp = kpk / K

    tau_i = c * (tau0 ** d)
    Ti = tau_i * T

    tau_d = e * (tau0 ** f)
    Td = tau_d * T

    return Kp, Ti, Td, "-"


# --------------------------------------------------------------------------------
# 7. Funciones de sintonización para Rovira et al. (1969)
# --------------------------------------------------------------------------------
def tune_rovira_PI(tau0, K, T, params):
    a = params['a']
    b = params['b']
    c = params['c']
    d = params['d']

    kpk = a * (tau0 ** b)
    Kp = kpk / K

    denom = c + d * tau0
    tau_i = (1.0 / denom) if denom != 0 else 0.0
    Ti = tau_i * T

    return Kp, Ti, 0.0, "-"


def tune_rovira_PID(tau0, K, T, params):
    a = params['a']
    b = params['b']
    c = params['c']
    d = params['d']
    e = params['e']
    f = params['f']

    kpk = a * (tau0 ** b)
    Kp = kpk / K

    tau_i = c + d * tau0
    Ti = tau_i * T

    tau_d = e + f * tau0
    Td = tau_d * T

    return Kp, Ti, Td, "-"


# --------------------------------------------------------------------------------
# 8. Funciones para imprimir tablas separadas: PI (sin Td) y PID (con Td)
# --------------------------------------------------------------------------------
def display_pi_table(results_pi):
    """
    Imprime la tabla de todos los controladores PI (y P),
    ordenada por 'Método' en orden alfabético descendente.
    Sin columna de tiempo derivativo.
    """
    results_sorted = sorted(results_pi,
            key=lambda x: (x['Modo'], x['Método']),
            reverse=True)
    headers = ["Método", "Variante", "Modo", "Ms/Criterio", "Kp", "Ti", "β"]
    table = []
    for r in results_sorted:
        table.append([
            r['Método'],
            r['Variante'],
            r['Modo'],
            r['Ms/Criterio'],
            f"{r['Kp']:.4f}",
            f"{r['Ti']:.4f}",
            r['β'] if isinstance(r['β'], str) else f"{r['β']:.4f}"
        ])
    print("\nTABLA de CONTROLADORES PI (y P):\n")
    print(tabulate(table, headers=headers, tablefmt="grid", stralign="center"))


def display_pid_table(results_pid):
    """
    Imprime la tabla de todos los controladores PID,
    ordenada por 'Método' en orden alfabético descendente.
    Incluye columna Td.
    """
    results_sorted = sorted(results_pid,
            key=lambda x: (x['Modo'], x['Método']),
            reverse=True)
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
    print("\nTABLA de CONTROLADORES PID:\n")
    print(tabulate(table, headers=headers, tablefmt="grid", stralign="center"))


# --------------------------------------------------------------------------------
# 9. Main: arme la lista de resultados y luego separe en PI vs PID antes de imprimir.
# --------------------------------------------------------------------------------
def main():
    # 1) Parsear argumentos desde terminal
    K, T, a, tau0 = parse_args()

    # 2) Obtener coeficientes
    usort_coeffs  = get_usort_coeffs()
    iae_reg, itae_reg, iae_ser, itae_ser = get_mendez_coeffs()
    lopez_coeffs  = get_lopez_coeffs()
    rovira_coeffs = get_rovira_coeffs()

    # 3) Lista para almacenar TODOS los resultados (PI y PID juntos)
    all_results = []

    # 4) uSORT1 y uSORT2 (PI y PID) para cada modo, cada Ms, cada tipo (PI/PID)
    for modo in ['regulador', 'servo']:
        for controlador in ['PI', 'PID']:
            for Ms, coeffs in usort_coeffs[modo][controlador].items():
                # uSORT1
                if modo == 'regulador':
                    Kp1, Ti1, Td1, beta1 = tune_usort1_reg(a, tau0, K, T, coeffs)
                else:
                    Kp1, Ti1, Td1, beta1 = tune_usort1_servo(a, tau0, K, T, coeffs)

                all_results.append({
                    'Método'      : "uSORT1",
                    'Variante'    : f"{controlador} 1GdL",
                    'Modo'        : modo.capitalize(),
                    'Ms/Criterio' : f"{Ms:.1f}",
                    'Kp'          : Kp1,
                    'Ti'          : Ti1,
                    'Td'          : Td1,
                    'β'           : beta1
                })

                # uSORT2
                if modo == 'regulador':
                    Kp2, Ti2, Td2, beta2 = tune_usort2_reg(a, tau0, K, T, coeffs)
                else:
                    Kp2, Ti2, Td2, beta2 = tune_usort2_servo(a, tau0, K, T, coeffs)

                all_results.append({
                    'Método'      : "uSORT2",
                    'Variante'    : f"{controlador} 2GdL",
                    'Modo'        : modo.capitalize(),
                    'Ms/Criterio' : f"{Ms:.1f}",
                    'Kp'          : Kp2,
                    'Ti'          : Ti2,
                    'Td'          : Td2,
                    'β'           : beta2
                })

    # 5) Méndez & Rímolo (Regulador y Servo, IAE e ITAE) – solo PI
    for crit, coeff_dict_reg, coeff_dict_ser in [
        ('IAE', iae_reg, iae_ser),
        ('ITAE', itae_reg, itae_ser)
    ]:
        if a not in coeff_dict_reg or a not in coeff_dict_ser:
            print(f"ERROR: No hay coeficientes de Méndez & Rímolo para a = {a}.")
            sys.exit(1)

        # Regulador
        coeffs_mr_r = coeff_dict_reg[a]
        if crit == 'IAE':
            Kpr_r, Tir_r, Tdr_r, betar_r = tune_mendez_reg_IAE(a, tau0, K, T, coeffs_mr_r)
        else:
            Kpr_r, Tir_r, Tdr_r, betar_r = tune_mendez_reg_ITAE(a, tau0, K, T, coeffs_mr_r)

        all_results.append({
            'Método'      : "Méndez & Rímolo",
            'Variante'    : f"{crit} (PI)",
            'Modo'        : "Regulador",
            'Ms/Criterio' : crit,
            'Kp'          : Kpr_r,
            'Ti'          : Tir_r,
            'Td'          : Tdr_r,
            'β'           : betar_r
        })

        # Servo
        coeffs_mr_s = coeff_dict_ser[a]
        if crit == 'IAE':
            Kpr_s, Tir_s, Tdr_s, betar_s = tune_mendez_ser_IAE(a, tau0, K, T, coeffs_mr_s)
        else:
            Kpr_s, Tir_s, Tdr_s, betar_s = tune_mendez_ser_ITAE(a, tau0, K, T, coeffs_mr_s)

        all_results.append({
            'Método'      : "Méndez & Rímolo",
            'Variante'    : f"{crit} (PI)",
            'Modo'        : "Servo",
            'Ms/Criterio' : crit,
            'Kp'          : Kpr_s,
            'Ti'          : Tir_s,
            'Td'          : Tdr_s,
            'β'           : betar_s
        })

    # 6) López et al. (Regulador – P, PI, PID – ISE, IAE, ITAE)
    lopez = lopez_coeffs
    for ctrl_type in ['P', 'PI', 'PID']:
        for crit in ['ISE', 'IAE', 'ITAE']:
            params = lopez[ctrl_type][crit]
            if ctrl_type == 'P':
                Kpl, Til, Tdl, betal = tune_lopez_P(tau0, K, params)
            elif ctrl_type == 'PI':
                Kpl, Til, Tdl, betal = tune_lopez_PI(tau0, K, T, params)
            else:  # 'PID'
                Kpl, Til, Tdl, betal = tune_lopez_PID(tau0, K, T, params)

            all_results.append({
                'Método'      : "López et al.",
                'Variante'    : f"{ctrl_type} ({crit})",
                'Modo'        : "Regulador",
                'Ms/Criterio' : crit,
                'Kp'          : Kpl,
                'Ti'          : Til,
                'Td'          : Tdl,
                'β'           : betal
            })

    # 7) Rovira et al. (Servo – PI, PID – IAE, ITAE)
    rovira = rovira_coeffs
    for ctrl_type in ['PI', 'PID']:
        for crit in ['IAE', 'ITAE']:
            params = rovira[ctrl_type][crit]
            if ctrl_type == 'PI':
                Kpr, Tir, Tdr, betar = tune_rovira_PI(tau0, K, T, params)
            else:  # 'PID'
                Kpr, Tir, Tdr, betar = tune_rovira_PID(tau0, K, T, params)

            all_results.append({
                'Método'      : "Rovira et al.",
                'Variante'    : f"{ctrl_type} ({crit})",
                'Modo'        : "Servo",
                'Ms/Criterio' : crit,
                'Kp'          : Kpr,
                'Ti'          : Tir,
                'Td'          : Tdr,
                'β'           : betar
            })

    # 8) Separar en listas: PI (y P) vs PID
    pi_results  = []
    pid_results = []
    for entry in all_results:
        var = entry['Variante']
        # “PID” en la cadena de Variante, pero no confundir con “P (ISE)” o “P (IAE)”
        if "PID" in var and not var.startswith("P ("):
            pid_results.append(entry)
        else:
            pi_results.append(entry)

    # 9) Imprimir las dos tablas
    display_pi_table(pi_results)
    display_pid_table(pid_results)


if __name__ == "__main__":
    main()


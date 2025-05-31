#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graficTuning_pyqt_filters_reduced.py

Versión adaptada del script de sintonización para usar PyQt5 y mostrar los
resultados en una tabla gráfica. Permite seleccionar filas completas y
filtrar por Modo y Método únicamente.

Calcula parámetros de control (Kp, Ti, Td, β) con métodos:
  • uSORT1   (PI 1GdL / PID 1GdL)
  • uSORT2   (PI 2GdL / PID 2GdL)
  • Méndez & Rímolo   (Regulador/Servo, IAE e ITAE, solo PI)
  • López et al.      (P, PI, PID – Regulador – ISE, IAE, ITAE)
  • Rovira et al.     (PI, PID – Servo – IAE, ITAE)

Luego muestra los resultados en un QTableView con un CustomSortFilterProxyModel
para permitir ordenar al hacer clic en las cabeceras y filtrar por:
  - Modo (Regulador/Servo)
  - Método

También permite editar los parámetros (K, T, a, τ₀) desde la interfaz y recalcular.
"""

import sys
from typing import List, Any, Dict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableView, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem


# ============================
# 1) Funciones y coeficientes de sintonización
# ============================

def get_usort_coeffs():
    return {
        'regulador': {
            'PI': {
                2.0: {
                    'a0': 0.265,  'a1': 0.603,  'a2': -0.971,
                    'b0': -1.382, 'b1':  2.837, 'b2':  0.211,
                    'c0': 0.0,    'c1':  0.0,   'c2':  0.0,
                    'd0': 0.372,  'd1':  1.205, 'd2':  0.608
                },
                1.6: {
                    'a0': 0.175,  'a1': 0.466,  'a2': -0.911,
                    'b0': -1.382, 'b1':  2.837, 'b2':  0.211,
                    'c0': 0.0,    'c1':  0.0,   'c2':  0.0,
                    'd0': 0.446,  'd1':  0.811, 'd2':  0.446
                }
            },
            'PID': {
                2.0: {
                    'a0': 0.235,  'a1': 0.840,  'a2': -0.919,
                    'b0': -0.198, 'b1': 1.291,  'b2':  0.485,
                    'c0':  0.004, 'c1': 0.389,  'c2':  0.869,
                    'd0':  0.248, 'd1': 0.571,  'd2':  0.362
                },
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
                1.8: {
                    'a0':  0.243, 'a1':  0.509, 'a2': -1.063,
                    'b0': 14.650, 'b1':  8.450, 'b2':  0.000, 'b3': 15.740,
                    'c0':  0.0,   'c1':  0.0,   'c2':  0.0,
                    'd0':  0.372, 'd1':  1.205, 'd2':  0.608
                },
                1.6: {
                    'a0':  0.209, 'a1':  0.417, 'a2': -1.064,
                    'b0':  0.107, 'b1':  1.164, 'b2':  0.377, 'b3':  0.066,
                    'c0':  0.0,   'c1':  0.0,   'c2':  0.0,
                    'd0':  0.446, 'd1':  0.811, 'd2':  0.446
                }
            },
            'PID': {
                1.8: {
                    'a0':  0.377,  'a1':  0.727,  'a2': -1.041,
                    'b0':  1.687,  'b1': 339.2,  'b2': 39.86, 'b3': 1299.0,
                    'c0': -0.016,  'c1':  0.333,  'c2':  0.815,
                    'd0':  0.248,  'd1':  0.571, 'd2':  0.362
                },
                1.6: {
                    'a0':  0.502,  'a1':  0.518,  'a2': -1.194,
                    'b0':  0.135,  'b1':  1.355,  'b2':  0.333, 'b3':  0.403,
                    'c0':  0.026,  'c1':  0.403,  'c2':  0.613,
                    'd0':  0.255,  'd1':  0.277, 'd2':  0.476
                }
            }
        }
    }


def get_mendez_coeffs():
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


# --- Funciones de sintonización para cada método ---

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


def construir_y_ordenar_resultados(
    K: float, T: float, a: float, tau0: float
) -> List[Dict[str, Any]]:
    usort_coeffs  = get_usort_coeffs()
    iae_reg, itae_reg, iae_ser, itae_ser = get_mendez_coeffs()
    lopez_coeffs  = get_lopez_coeffs()
    rovira_coeffs = get_rovira_coeffs()

    all_results: List[Dict[str, Any]] = []

    # 1) uSORT1 y uSORT2 (PI y PID)
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

    # 2) Méndez & Rímolo (Regulador y Servo, IAE e ITAE) – solo PI
    for crit, coeff_dict_reg, coeff_dict_ser in [
        ('IAE', iae_reg, iae_ser),
        ('ITAE', itae_reg, itae_ser)
    ]:
        if a not in coeff_dict_reg or a not in coeff_dict_ser:
            raise ValueError(f"No hay coeficientes de Méndez & Rímolo para a = {a}.")

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

    # 3) López et al. (Regulador – P, PI, PID – ISE, IAE, ITAE)
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

    # 4) Rovira et al. (Servo – PI, PID – IAE, ITAE)
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

    # 5) Ordenamos TODO en una sola lista (orden inicial)
    def ms_a_float(valor: str) -> float:
        try:
            return float(valor)
        except ValueError:
            return float("inf")

    all_results.sort(
        key=lambda x: (
            x['Variante'],                # 1° Por Variante
            x['Método'],                  # 2° Por Método
            x['Modo'],                    # 3° Por Modo
            ms_a_float(x['Ms/Criterio'])  # 4° Por Ms/Criterio numérico
        )
    )

    return all_results


# ============================
# 2) CustomSortFilterProxyModel para filtros reducidos
# ============================

class CustomSortFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy que filtra filas con base en:
      - Modo (columna 2)
      - Método (columna 1)
    Cada filtro se compara con igualdad exacta, o se ignora si el valor es "Todos".
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_modo = "Todos"
        self.filter_metodo = "Todos"

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()

        # Columna 2 = Modo
        index_modo = model.index(source_row, 2, source_parent)
        data_modo = model.data(index_modo, Qt.DisplayRole)
        if self.filter_modo != "Todos" and data_modo != self.filter_modo:
            return False

        # Columna 1 = Método
        index_met = model.index(source_row, 1, source_parent)
        data_met = model.data(index_met, Qt.DisplayRole)
        if self.filter_metodo != "Todos" and data_met != self.filter_metodo:
            return False

        return True


# ============================
# 3) Clase principal de la GUI con PyQt5
# ============================

class TuningWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sintonización de Controladores (PyQt5)")
        self.setMinimumSize(900, 600)

        # Layout principal vertical
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # --------- 3.1) Zona de parámetros (K, T, a, tau0) y botón “Calcular” ---------
        params_layout = QHBoxLayout()
        main_layout.addLayout(params_layout)

        params_layout.addWidget(QLabel("K:"))
        self.edit_K = QLineEdit("1.0")
        self.edit_K.setFixedWidth(80)
        params_layout.addWidget(self.edit_K)

        params_layout.addWidget(QLabel("T:"))
        self.edit_T = QLineEdit("1.0")
        self.edit_T.setFixedWidth(80)
        params_layout.addWidget(self.edit_T)

        params_layout.addWidget(QLabel("a:"))
        self.combo_a = QComboBox()
        for val in ["0.0", "0.25", "0.5", "0.75", "1.0"]:
            self.combo_a.addItem(val)
        self.combo_a.setFixedWidth(80)
        params_layout.addWidget(self.combo_a)

        params_layout.addWidget(QLabel("τ₀:"))
        self.edit_tau0 = QLineEdit("0.0")
        self.edit_tau0.setFixedWidth(80)
        params_layout.addWidget(self.edit_tau0)

        self.btn_calcular = QPushButton("Calcular")
        self.btn_calcular.setFixedWidth(120)
        params_layout.addWidget(self.btn_calcular)

        params_layout.addStretch()

        # --------- 3.2) Zona de filtros por Modo y Método ---------
        filtro_layout = QHBoxLayout()
        main_layout.addLayout(filtro_layout)

        filtro_layout.addWidget(QLabel("Filtrar Modo:"))
        self.combo_filtro_modo = QComboBox()
        self.combo_filtro_modo.addItem("Todos")
        self.combo_filtro_modo.addItem("Regulador")
        self.combo_filtro_modo.addItem("Servo")
        self.combo_filtro_modo.setFixedWidth(120)
        filtro_layout.addWidget(self.combo_filtro_modo)

        filtro_layout.addWidget(QLabel("Filtrar Método:"))
        self.combo_filtro_metodo = QComboBox()
        self.combo_filtro_metodo.addItem("Todos")
        self.combo_filtro_metodo.setFixedWidth(200)
        filtro_layout.addWidget(self.combo_filtro_metodo)

        filtro_layout.addStretch()

        # --------- 3.3) Tabla de resultados (QTableView con modelo y proxy) ---------
        # Modelo de datos (origen)
        self.modelo_origen = QStandardItemModel(0, 8, self)  # 8 columnas
        self.modelo_origen.setHorizontalHeaderLabels([
            "Variante", "Método", "Modo", "Ms/Criterio", "Kp", "Ti", "Td", "β"
        ])

        # Proxy para orden y filtrado
        self.proxy = CustomSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.modelo_origen)

        # Vista de tabla
        self.tabla = QTableView()
        self.tabla.setModel(self.proxy)
        self.tabla.setSortingEnabled(True)           # Permite ordenar al hacer clic en cabecera
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)

        # Selección por fila completa y una sola fila seleccionable
        self.tabla.setSelectionBehavior(QTableView.SelectRows)
        self.tabla.setSelectionMode(QTableView.SingleSelection)

        main_layout.addWidget(self.tabla)

        # --------- 3.4) Estado interno ---------
        self.todos_resultados: List[Dict[str, Any]] = []

        # Conexiones de señales
        self.btn_calcular.clicked.connect(self._on_calcular)
        self.combo_filtro_modo.currentTextChanged.connect(self._on_filtrar)
        self.combo_filtro_metodo.currentTextChanged.connect(self._on_filtrar)

    def _on_calcular(self):
        """
        Lee K, T, a, tau0 de los widgets, calcula resultados y llena la tabla.
        También actualiza el QComboBox de método con las opciones únicas
        detectadas en los resultados.
        """
        # Validar y convertir entradas
        try:
            K = float(self.edit_K.text())
            T = float(self.edit_T.text())
            a = float(self.combo_a.currentText())
            tau0 = float(self.edit_tau0.text())
        except ValueError:
            QMessageBox.critical(self, "Error de entrada", "Los valores de K, T y τ₀ deben ser números válidos.")
            return

        if K <= 0 or T <= 0:
            QMessageBox.critical(self, "Error de rango", "K y T deben ser mayores que 0.")
            return

        allowed_a = {0.0, 0.25, 0.5, 0.75, 1.0}
        if a not in allowed_a:
            QMessageBox.critical(
                self, "Error de rango",
                f"El valor de a debe ser uno de {sorted(allowed_a)}. Usted ingresó {a}."
            )
            return

        if tau0 < 0:
            QMessageBox.critical(self, "Error de rango", "τ₀ debe ser un valor no negativo.")
            return

        # Llamar a la función de sintonización para obtener la lista ordenada
        try:
            self.todos_resultados = construir_y_ordenar_resultados(K, T, a, tau0)
        except Exception as e:
            QMessageBox.critical(self, "Error al calcular", str(e))
            return

        # Llenar la tabla con los resultados completos
        self._llenar_modelo_origen()

        # Rellenar el combo_filtro_metodo con valores únicos de Método detectados
        self._populate_method_combo()

        # Aplicar el filtro actual (si se había seleccionado alguno previamente)
        self._apply_filters()

        # Ajustar tamaño de columnas según contenido
        self.tabla.resizeColumnsToContents()

    def _llenar_modelo_origen(self):
        """
        Llena el modelo de origen con TODAS las filas de self.todos_resultados,
        sin aplicar aún ningún filtro.
        """
        # Limpiar modelo
        self.modelo_origen.removeRows(0, self.modelo_origen.rowCount())

        for r in self.todos_resultados:
            variante = QStandardItem(r["Variante"])
            metodo   = QStandardItem(r["Método"])
            modo     = QStandardItem(r["Modo"])
            ms       = QStandardItem(str(r["Ms/Criterio"]))
            kp       = QStandardItem(f"{r['Kp']:.4f}")
            ti       = QStandardItem(f"{r['Ti']:.4f}")
            td       = QStandardItem(f"{r['Td']:.4f}")
            beta     = QStandardItem(r["β"] if isinstance(r["β"], str) else f"{r['β']:.4f}")

            # Alineación centrada en las columnas numéricas
            kp.setTextAlignment(Qt.AlignCenter)
            ti.setTextAlignment(Qt.AlignCenter)
            td.setTextAlignment(Qt.AlignCenter)
            beta.setTextAlignment(Qt.AlignCenter)
            ms.setTextAlignment(Qt.AlignCenter)

            self.modelo_origen.appendRow([variante, metodo, modo, ms, kp, ti, td, beta])

    def _populate_method_combo(self):
        """
        Extrae los valores únicos de 'Método' de self.todos_resultados
        y los usa para llenar (o actualizar) el QComboBox combo_filtro_metodo.
        Siempre incluye primero el elemento 'Todos'.
        """
        metodos = set(r["Método"] for r in self.todos_resultados)
        metodos_list = sorted(metodos)

        current_met = self.combo_filtro_metodo.currentText()
        self.combo_filtro_metodo.blockSignals(True)
        self.combo_filtro_metodo.clear()
        self.combo_filtro_metodo.addItem("Todos")
        for m in metodos_list:
            self.combo_filtro_metodo.addItem(m)
        if current_met in metodos_list:
            self.combo_filtro_metodo.setCurrentText(current_met)
        else:
            self.combo_filtro_metodo.setCurrentText("Todos")
        self.combo_filtro_metodo.blockSignals(False)

    def _on_filtrar(self):
        """
        Se dispara cuando cambia cualquiera de los QComboBox de filtro.
        Simplemente reaplica todos los filtros en el proxy.
        """
        self._apply_filters()

    def _apply_filters(self):
        """
        Lee los valores actuales de los QComboBox de filtro y los asigna
        a los atributos de filtro del proxy, luego invalida el filtro para
        que se refresque la vista.
        """
        modo_sel = self.combo_filtro_modo.currentText()
        met_sel = self.combo_filtro_metodo.currentText()

        self.proxy.filter_modo = modo_sel
        self.proxy.filter_metodo = met_sel

        self.proxy.invalidateFilter()


# ============================
# 4) Bloque principal para lanzar la aplicación
# ============================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = TuningWindow()
    ventana.show()
    sys.exit(app.exec_())


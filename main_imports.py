import math
import sys
import random

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsTextItem, QMenuBar, QAction, qApp, QGridLayout, QStackedWidget, QTableWidgetItem,
    QTableWidget, QLineEdit, QLabel, QMessageBox
)
from PyQt5.QtGui import QBrush, QColor, QPolygonF, QPen, QFont, QPainter
from PyQt5.QtCore import QTimer, QPointF, Qt
import pyqtgraph as pg
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import serial
import struct
from time import sleep
from queue import Queue

import logging

logging.basicConfig(
    filename="niim.log",  # файл логов
    filemode="a",          # дописывать, не перезаписывать
    level=logging.DEBUG,   # уровень логирования
    format="%(asctime)s | %(levelname)s | %(message)s",
)
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


class Credits(QDialog):

    def __init__(self, parent=None):
        super(Credits, self).__init__(parent, Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        head = ['Icon', 'Attribution']
        icons = [
            [':/icons/open', 'Icon made by <a href="https://www.flaticon.com/authors/those-icons">Those Icons</a> from <a href="www.flaticon.com">www.flaticon.com</a>'],
            [':/icons/save', 'Icon made by <a href="https://www.flaticon.com/authors/vitaly-gorbachev">Vitaly Gorbachev</a> from <a href="www.flaticon.com">www.flaticon.com</a>'],
            [':/icons/play', 'Icon made by <a href="https://www.flaticon.com/authors/freepik">Freepik</a> from <a href="www.flaticon.com">www.flaticon.com</a>'],
            [':/icons/pause', 'Icon made by <a href="https://www.flaticon.com/authors/freepik">Freepik</a> from <a href="www.flaticon.com">www.flaticon.com</a>'],
            [':/icons/warning', 'Icon made by <a href="https://www.flaticon.com/authors/freepik">Freepik</a> from <a href="www.flaticon.com">www.flaticon.com</a>'],
            [':/icons/voxelize', '<a href="https://commons.wikimedia.org/wiki/User:Vossman">Vossman</a>; <a href="https://commons.wikimedia.org/wiki/User:Mwtoews">M. W. Toews</a> (<a href="https://creativecommons.org/licenses/by-sa/2.5/deed.en">Creative Commons</a>)'],
        ]

        self.setWindowTitle('Credits')
        self.layout = QVBoxLayout()
        self.table = QTableWidget(0, len(head))
        self.table.setHorizontalHeaderLabels(head)

        for row in icons:
            self.table.insertRow(self.table.rowCount())
            self.table.setItem(self.table.rowCount()-1, 0, QTableWidgetItem(QIcon(row[0]), ''))
            label = QLabel(row[1])
            label.setTextFormat(Qt.RichText)
            self.table.setCellWidget(self.table.rowCount()-1, 1, label)

        self.table.resizeColumnsToContents()
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.setMinimumSize(0.7*self.table.width(), 0.55*self.table.height())
        self.table.show()

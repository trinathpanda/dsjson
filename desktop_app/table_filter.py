"""Excel-style column filter and sort for the Data preview table.

- RowsFilterProxy: per-column value filters plus a search-all text; sorting is delegated
  to the source model (one Python list sort, fast on 100k+ rows).
- FilterHeader: header with a sort arrow and a funnel icon per column. Click the name to
  sort (ascending, then descending); click the funnel or right-click to filter.
- ColumnFilterPopup: list of distinct values with counts, search, select all, sort / clear sort.
"""

from __future__ import annotations

from collections import Counter

from PySide6.QtCore import QPoint, QRect, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

BLANK_LABEL = "(Blanks)"
MAX_LISTED_VALUES = 10000


def cell_text(value) -> str:
    return "" if value is None else str(value)


def sort_key(value):
    """Blanks first, then numbers numerically, then text case-insensitively."""
    if value is None or value == "":
        return (0, 0.0, "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (1, float(value), "")
    return (2, 0.0, str(value).casefold())


class RowsFilterProxy(QSortFilterProxyModel):
    """Filters rows by the allowed values of each filtered column."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.column_filters: dict[int, set[str]] = {}

    def _refilter(self, change) -> None:
        if not hasattr(self, "beginFilterChange"):  # Qt < 6.10
            change()
            self.invalidateFilter()
            return
        self.beginFilterChange()  # Qt 6.10+ replacement for invalidateFilter()
        change()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_column_filter(self, column: int, values: set[str] | None) -> None:
        if values is None:
            self._refilter(lambda: self.column_filters.pop(column, None))
        else:
            self._refilter(lambda: self.column_filters.__setitem__(column, values))

    def clear_filters(self) -> None:
        if self.column_filters:  # nothing to undo: skip a pass over every row
            self._refilter(self.column_filters.clear)

    def _passes(self, row: list, skip_column: int | None = None) -> bool:
        for column, allowed in self.column_filters.items():
            if column != skip_column and cell_text(row[column]) not in allowed:
                return False
        return True

    def filterAcceptsRow(self, source_row, source_parent) -> bool:  # noqa: N802 (Qt API)
        return self._passes(self.sourceModel().rows[source_row])

    def distinct_values(self, column: int) -> list[tuple[str, int]]:
        """Values of a column (with counts) among rows that pass the other filters, like Excel."""
        counts = Counter(row[column] for row in self.sourceModel().rows if self._passes(row, skip_column=column))
        merged: Counter = Counter()
        for value, count in counts.items():
            merged[cell_text(value)] += count
        seen, result = set(), []
        for value in sorted(counts, key=sort_key):
            text = cell_text(value)
            if text not in seen:
                seen.add(text)
                result.append((text, merged[text]))
        return result

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:
        self.sourceModel().sort(column, order)


class FilterHeader(QHeaderView):
    """Horizontal header: name click sorts, funnel click or right-click opens the filter."""

    filter_requested = Signal(int, QPoint)

    ICON = 12
    MARGIN = 6

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setObjectName("filterHeader")
        self.setSectionsClickable(True)
        self.setHighlightSections(False)
        self.filtered: set[int] = set()
        self._swallow_release = False

    def _icon_rect(self, logical: int) -> QRect:
        x = self.sectionViewportPosition(logical) + self.sectionSize(logical) - self.ICON - self.MARGIN
        return QRect(x - 2, 0, self.ICON + 6, self.height())

    def paintSection(self, painter: QPainter, rect: QRect, logical: int) -> None:  # noqa: N802 (Qt API)
        painter.save()
        super().paintSection(painter, rect, logical)
        painter.restore()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        x = rect.right() - self.ICON - self.MARGIN + 1
        y = rect.center().y() - self.ICON // 2 + 1
        active = logical in self.filtered
        funnel = QPolygon([
            QPoint(x, y), QPoint(x + 12, y), QPoint(x + 7, y + 6),
            QPoint(x + 7, y + 11), QPoint(x + 5, y + 10), QPoint(x + 5, y + 6),
        ])
        color = QColor("#60A5FA" if active else "#64748B")
        painter.setPen(QPen(color, 1.2))
        painter.setBrush(color if active else Qt.NoBrush)
        painter.drawPolygon(funnel)

        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logical:
            ax, ay = x - 14, rect.center().y()
            up = self.sortIndicatorOrder() == Qt.AscendingOrder
            arrow = QPolygon(
                [QPoint(ax, ay + 3), QPoint(ax + 8, ay + 3), QPoint(ax + 4, ay - 3)] if up
                else [QPoint(ax, ay - 3), QPoint(ax + 8, ay - 3), QPoint(ax + 4, ay + 3)]
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#E2E8F0"))
            painter.drawPolygon(arrow)
        painter.restore()

    def _request(self, logical: int) -> None:
        x = self.sectionViewportPosition(logical)
        self.filter_requested.emit(logical, self.mapToGlobal(QPoint(max(x, 0), self.height())))

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        pos = event.position().toPoint()
        logical = self.logicalIndexAt(pos)
        if event.button() == Qt.LeftButton and logical >= 0 and self._icon_rect(logical).contains(pos):
            self._swallow_release = True  # funnel click must not also sort
            self._request(logical)
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self._swallow_release:
            self._swallow_release = False
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (Qt API)
        logical = self.logicalIndexAt(event.pos())
        if logical >= 0:
            self._request(logical)


class ColumnFilterPopup(QFrame):
    """Excel-like value picker for one column."""

    applied = Signal(object)  # set[str] of allowed values, or None for "no filter"
    sort_requested = Signal(object)  # Qt.SortOrder, or None to clear the sort
    closed = Signal()

    def __init__(self, title: str, values: list[tuple[str, int]], selected: set[str] | None, parent=None) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("popup")
        self.setMinimumWidth(300)
        self._all_values = {v for v, _ in values}

        heading = QLabel(title)
        heading.setObjectName("stepTitle")

        sort_asc = QPushButton("Sort A to Z")
        sort_desc = QPushButton("Sort Z to A")
        sort_asc.clicked.connect(lambda: self._sort(Qt.AscendingOrder))
        sort_desc.clicked.connect(lambda: self._sort(Qt.DescendingOrder))
        sort_row = QHBoxLayout()
        sort_row.addWidget(sort_asc)
        sort_row.addWidget(sort_desc)
        clear_sort = QPushButton("Clear sort")
        clear_sort.clicked.connect(lambda: self._sort(None))
        sort_row.addWidget(clear_sort)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search values")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._search_changed)

        self.select_all = QCheckBox("(Select all)")
        self.select_all.clicked.connect(self._toggle_all)

        self.list = QListWidget()
        self.list.setMinimumHeight(240)
        self.list.setUniformItemSizes(True)
        # shortcut: lists the first MAX_LISTED_VALUES distinct values only; raise it if columns need more
        for value, count in values[:MAX_LISTED_VALUES]:
            item = QListWidgetItem(f"{value or BLANK_LABEL}    ({count:,})")
            item.setData(Qt.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if selected is None or value in selected else Qt.Unchecked)
            self.list.addItem(item)
        self.list.itemChanged.connect(self._sync_select_all)
        listed = f", first {MAX_LISTED_VALUES:,} listed" if len(values) > MAX_LISTED_VALUES else ""
        note = QLabel(f"{len(values):,} distinct values{listed}")
        note.setObjectName("muted")

        clear = QPushButton("Clear filter")
        clear.clicked.connect(lambda: self._finish(None))
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        ok = QPushButton("OK")
        ok.setObjectName("primarySmall")
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        self.search.returnPressed.connect(self._ok)
        buttons = QHBoxLayout()
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(heading)
        layout.addLayout(sort_row)
        layout.addWidget(self.search)
        layout.addWidget(self.select_all)
        layout.addWidget(self.list, 1)
        layout.addWidget(note)
        layout.addLayout(buttons)
        self._sync_select_all()
        self.search.setFocus()

    def hideEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.closed.emit()
        super().hideEvent(event)

    def _visible_items(self):
        return [self.list.item(i) for i in range(self.list.count()) if not self.list.item(i).isHidden()]

    def _search_changed(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(needle) and needle not in (item.data(Qt.UserRole) or BLANK_LABEL).lower())
        self._sync_select_all()

    def _toggle_all(self, checked: bool) -> None:
        self.list.blockSignals(True)
        for item in self._visible_items():
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.list.blockSignals(False)
        self._sync_select_all()

    def _sync_select_all(self, *_) -> None:
        visible = self._visible_items()
        self.select_all.setChecked(bool(visible) and all(i.checkState() == Qt.Checked for i in visible))

    def _sort(self, order) -> None:
        self.sort_requested.emit(order)
        self.close()

    def _ok(self) -> None:
        # Excel rule: with a search typed, only the matching ticked values are kept
        chosen = {i.data(Qt.UserRole) for i in self._visible_items() if i.checkState() == Qt.Checked}
        self._finish(None if chosen == self._all_values else chosen)

    def _finish(self, values: set[str] | None) -> None:
        self.applied.emit(values)
        self.close()

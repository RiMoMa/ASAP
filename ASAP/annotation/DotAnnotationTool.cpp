#include "DotAnnotationTool.h"
#include "DotQtAnnotation.h"
#include <QAction>
#include <QApplication>
#include <QStyleHints>
#include "../PathologyViewer.h"
#include "AnnotationWorkstationExtensionPlugin.h"
#include "core/Point.h"

DotAnnotationTool::DotAnnotationTool(AnnotationWorkstationExtensionPlugin* annotationPlugin, PathologyViewer* viewer) : 
  AnnotationTool(annotationPlugin, viewer)
{
}

void DotAnnotationTool::mousePressEvent(QMouseEvent *event) {
  AnnotationTool::mousePressEvent(event);
  if (_generating) {
    _annotationPlugin->finishAnnotation();
    _start = Point(-1, -1);
    _last = _start;
    _generating = false;
  }
  event->accept();
}

QAction* DotAnnotationTool::getToolButton() {
  if (!_button) {
    _button = new QAction("&DotAnnotation", this);
    _button->setObjectName(QString::fromStdString(name()));
#if QT_VERSION >= QT_VERSION_CHECK(6, 5, 0)
    const bool dark = QApplication::styleHints()->colorScheme() == Qt::ColorScheme::Dark;
#else
    const bool dark = false;
#endif
    if (dark) {
        _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/dot_dark.png")));
    }
    else {
        _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/dot.png")));
    }
    _button->setShortcut(QKeySequence("d"));
  }
  return _button;
}

std::string DotAnnotationTool::name() {
  return std::string("dotannotation");
}
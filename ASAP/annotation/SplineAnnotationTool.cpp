#include "SplineAnnotationTool.h"
#include <QAction>
#include <QPixmap>
#include <QIcon>
#include <QApplication>
#include <QStyleHints>
#include "AnnotationWorkstationExtensionPlugin.h"
#include "../PathologyViewer.h"

SplineAnnotationTool::SplineAnnotationTool(AnnotationWorkstationExtensionPlugin* annotationPlugin, PathologyViewer* viewer) :
PolyAnnotationTool(annotationPlugin, viewer)
{
}

QAction* SplineAnnotationTool::getToolButton() {
  if (!_button) {
    _button = new QAction("&SplineAnnotation", this);
    _button->setObjectName(QString::fromStdString(name()));
#if QT_VERSION >= QT_VERSION_CHECK(6, 5, 0)
    const bool dark = QApplication::styleHints()->colorScheme() == Qt::ColorScheme::Dark;
#else
    const bool dark = false;
#endif
    if (dark) {
        _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/spline_dark.png")));
    }
    else {
        _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/spline.png")));
    }
    _button->setShortcut(QKeySequence("s"));
  }
  return _button;
}

std::string SplineAnnotationTool::name() {
  return std::string("splineannotation");
}
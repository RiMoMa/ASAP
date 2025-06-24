#include "GlandDetectionTool.h"
#include "AnnotationWorkstationExtensionPlugin.h"
#include "../PathologyViewer.h"
#include "core/Point.h"
#include "multiresolutionimageinterface/MultiResolutionImage.h"

#include <QAction>
#include <QApplication>
#include <QStyleHints>
#include <QProcess>
#include <QDebug>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>

#ifndef SCRIPTS_DIR
#define SCRIPTS_DIR "."
#endif

GlandDetectionTool::GlandDetectionTool(AnnotationWorkstationExtensionPlugin* plugin, PathologyViewer* viewer)
{
    _annotationPlugin = plugin;
    _viewer = viewer;
}

std::string GlandDetectionTool::name()
{
    return std::string("glanddetection");
}

QAction* GlandDetectionTool::getToolButton()
{
    if (!_button) {
        _button = new QAction("&Detect Glands", this);
        _button->setObjectName(QString::fromStdString(name()));
#if QT_VERSION >= QT_VERSION_CHECK(6, 5, 0)
        const bool dark = QApplication::styleHints()->colorScheme() == Qt::ColorScheme::Dark;
#else
        const bool dark = false;
#endif
        if (dark) {
            _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/pointset_dark.png")));
        } else {
            _button->setIcon(QIcon(QPixmap(":/AnnotationWorkstationExtensionPlugin_icons/pointset.png")));
        }
        connect(_button, &QAction::triggered, this, &GlandDetectionTool::runDetection);
    }
    return _button;
}

void GlandDetectionTool::runDetection()
{
    if (!_viewer || !_annotationPlugin)
        return;
    QRectF FOV = _viewer->mapToScene(_viewer->rect()).boundingRect();
    float scale = _viewer->getSceneScale();
    int x = static_cast<int>(FOV.left() / scale);
    int y = static_cast<int>(FOV.top() / scale);
    int w = static_cast<int>(FOV.width() / scale);
    int h = static_cast<int>(FOV.height() / scale);

    std::shared_ptr<MultiResolutionImage> img = _annotationPlugin->getCurrentImage().lock();
    if (!img)
        return;
    QString slidePath = QString::fromStdString(img->getFilePath());
    if (slidePath.isEmpty())
        return;

    QString xmlPath = QFileInfo(slidePath).path() + "/" + QFileInfo(slidePath).completeBaseName() + ".xml";
    QString script = QStringLiteral(SCRIPTS_DIR) + "/detect_glands_fov.py";

    QStringList args;
    args << script << slidePath
         << "--x" << QString::number(x)
         << "--y" << QString::number(y)
         << "--width" << QString::number(w)
         << "--height" << QString::number(h)
         << "--out" << xmlPath
         << "--stdout";

    QProcess proc;
    proc.setProcessChannelMode(QProcess::MergedChannels);
    qDebug() << "Running" << "python3" << args.join(' ');
    proc.start("python3", args);
    if (!proc.waitForFinished(-1)) {
        qWarning() << "Gland detection script failed:" << proc.errorString();
        return;
    }
    QByteArray output = proc.readAll();
    qDebug().noquote() << output;
    QJsonDocument doc = QJsonDocument::fromJson(output);
    if (!doc.isArray())
        return;
    QJsonArray arr = doc.array();
    for (const QJsonValue& v : arr) {
        QJsonObject obj = v.toObject();
        QJsonArray coordsArr = obj["coords"].toArray();
        std::vector<Point> coords;
        for (const QJsonValue& c : coordsArr) {
            QJsonArray xy = c.toArray();
            if (xy.size() >= 2)
                coords.emplace_back(xy[0].toDouble(), xy[1].toDouble());
        }
        if (!coords.empty())
            _annotationPlugin->addPolygonAnnotation(coords);
    }
}


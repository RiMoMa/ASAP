#ifndef GLANDDETECTIONTOOL_H
#define GLANDDETECTIONTOOL_H

#include "interfaces/interfaces.h"
#include "annotationplugin_export.h"

class AnnotationWorkstationExtensionPlugin;
class PathologyViewer;

class ANNOTATIONPLUGIN_EXPORT GlandDetectionTool : public ToolPluginInterface
{
    Q_OBJECT
public:
    GlandDetectionTool(AnnotationWorkstationExtensionPlugin* plugin, PathologyViewer* viewer);
    std::string name() override;
    QAction* getToolButton() override;

private slots:
    void runDetection();

private:
    AnnotationWorkstationExtensionPlugin* _annotationPlugin;
};

#endif

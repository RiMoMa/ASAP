#ifndef UNETDETECTIONTOOL_H
#define UNETDETECTIONTOOL_H

#include "interfaces/interfaces.h"
#include "annotationplugin_export.h"

class AnnotationWorkstationExtensionPlugin;
class PathologyViewer;

class ANNOTATIONPLUGIN_EXPORT UnetDetectionTool : public ToolPluginInterface
{
    Q_OBJECT
public:
    UnetDetectionTool(AnnotationWorkstationExtensionPlugin* plugin, PathologyViewer* viewer);
    std::string name() override;
    QAction* getToolButton() override;

private slots:
    void runDetection();

private:
    AnnotationWorkstationExtensionPlugin* _annotationPlugin{nullptr};
};

#endif

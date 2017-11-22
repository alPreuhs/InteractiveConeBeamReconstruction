Im Ordner dependency sind die dependency files für vtk, ausserdem ist dort die whl für vtk die du installieren musst.
In dependency sind folgende files:

InteractorStyle: das ist ein (wer kann es glauben ;)) interactor style, der prinzipielle von der TrackballCamera ableitet. Er kann aber noch ein bisschen mehr (z.B. tastaturinput verarbeiten)
RenderWindowInteractor: das ist eigentlich ein file aus der VTK bibliothek, da ging aber irgendwas nicht, und man musste nen paar zeilen ändern (ich meine mich erinnern zu können dass das was mit pyqt5 kompatibilität zu tun hatte....)

Im base folder ist die klasse vtkWindow, sowie ein beispiel wie das vtk window geladen wird

vtkWindow: Klasse die in ein QFrame (Qframe muss übergeben werden) ein VTK fenster baut, hier kommt im prinizp der normale vtk code rein der deine scene visualisiert. Momentan wird hier ein STL geladen etwas verschoben und angezeigt.

Im ordner include ist das stl von einem kopf

Im ordner Math sind die klassen für das projektions mathe zeug
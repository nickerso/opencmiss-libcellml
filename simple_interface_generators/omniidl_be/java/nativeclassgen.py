import os
from omniidl import idlvisitor, output
import jnutils
import string

class NativeClassVisitor (idlvisitor.AstVisitor):
    def __init__(self):
        self.directoryParts = ['pjm2pcm']
        self.directory = ''
        self.package = ''
        try:
            os.mkdir('pjm2pcm')
        except OSError:
            pass

    def calculateDirectory(self):
        self.directory = string.join(self.directoryParts, '/')
        self.package = string.join(self.directoryParts, '.')
        
    def visitAST(self, node):
        for declaration in node.declarations():
            declaration.accept(self)
            
    def visitModule(self, node):
        try:
            os.mkdir(self.directory + '/' + node.identifier())
        except OSError:
            pass
        self.directoryParts.append(node.identifier())
        self.calculateDirectory()
        for defn in node.definitions():
            defn.accept(self)
        self.directoryParts.pop()
        self.calculateDirectory()
        
    def visitInterface(self, node):
        if not node.mainFile():
            return
        self.out = output.Stream(open(self.directory + '/' + jnutils.JavaName(node) + ".java", 'w'))
        self.out.out('package ' + self.package + ';')
        self.out.out('public class ' + jnutils.JavaName(node))
        self.out.out('  implements ' + jnutils.GetClassName(node))
        self.out.out('{')
        self.out.inc_indent()
        self.out.out('private ' + jnutils.JavaName(node) + '() {};')
        self.out.out('protected native void finalize();')
        self.out.out('public native int compareTo(Object obj);')
        self.out.out('public native boolean equals(Object obj);')
        self.out.out('public native int hashCode();')
        self.recurseAcceptInheritedContents(node)
        self.out.out('private long nativePtr;')
        self.out.dec_indent()
        self.out.out('};')
        self.out = None

    def recurseAcceptInheritedContents(self, node):
        self.out.out('private long nativePtr_' + string.join(node.scopedName(), '_') + ';')
        for i in node.contents():
            i.accept(self)
        for i in node.inherits():
            if i.scopedName() != ['XPCOM', 'IObject']:
                self.recurseAcceptInheritedContents(i)
        
    def visitAttribute(self, node):
        ti = jnutils.GetTypeInformation(node.attrType().unalias())
        for n in node.declarators():
            if not node.readonly():
                self.writeSetter(n, ti)
            self.writeGetter(n, ti)

    def writeSetter(self, node, ti):
        self.out.out('public native void ' + jnutils.AccessorName(node, 1) + '(' + ti.javaType(jnutils.Type.IN) + ' arg);')

    def writeGetter(self, node, ti):
        self.out.out('public native ' + ti.javaType(jnutils.Type.RETURN) + ' ' + jnutils.AccessorName(node, 0) + '();')
    
    def visitOperation(self, node):
        paramsig = ''
        for p in node.parameters():
            direction = [jnutils.Type.IN, jnutils.Type.OUT, jnutils.Type.INOUT][p.direction()]
            v = jnutils.GetTypeInformation(p.paramType().unalias()).\
                  javaType(direction) + ' ' +\
                  jnutils.JavaName(p)
            if paramsig != '':
                paramsig = paramsig + ', '
            paramsig = paramsig + v
        
        rti = jnutils.GetTypeInformation(node.returnType().unalias())
        self.out.out('public native ' + rti.javaType(jnutils.Type.RETURN) + ' ' +
                     jnutils.JavaName(node) + '(' + paramsig + ');')

def run(tree):
    iv = NativeClassVisitor()
    tree.accept(iv)

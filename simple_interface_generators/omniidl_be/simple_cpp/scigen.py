# -*- python -*-

from omniidl import idlvisitor, idlast, idltype;
from omniidl import output;
import os, string;
import conversionutils;
import simplecxx, corbacxx, identifier;

class Walker(idlvisitor.AstVisitor):
    """Walks over the AST once and writes the SCI header or SCI as it goes.
    """
    def visitAST(self, node):
        """Visit all the declarations in an AST"""

        self.beenIncluded = {}
        self.masterFile = node.file()
        self.masterGuard = ''
        self.scope = ["SCI"]
        self.scopeEntryDepth = 0
        for i in node.filebase:
            if (i >= 'a' and i <= 'z') or (i >= 'A' and i <= 'Z'):
                self.masterGuard = self.masterGuard + i
        self.sci.out("/* This file is automatically generated from " +\
                     node.filename + """
 * DO NOT EDIT DIRECTLY OR CHANGES WILL BE LOST!
 */""")
        if not self.doing_header:
            self.sci.out("""
#include <omniORB4/CORBA.h>
#include "cda_compiler_support.h"
#include <strings.h>
#include <wchar.h>
#include <exception>
#include "corba_support/WrapperRepository.hxx"
            """)
            self.sci.out('#ifndef MODULE_CONTAINS_' + self.masterGuard)
            self.sci.out('#define MODULE_CONTAINS_' + self.masterGuard)
            self.sci.out('#endif')
            self.sci.out('#include "CCI' + node.filebase + '.hxx"')
            self.sci.out('#include "SCI' + node.filebase + '.hxx"')
        else:
            self.sci.out('#include "cda_compiler_support.h"')
            self.sci.out('#ifndef _SCI' + self.masterGuard + '_hxx')
            self.sci.out('#define _SCI' + self.masterGuard + '_hxx')
            self.sci.out('#include "Iface' + node.filebase + '.hxx"')
            self.sci.out('#include "' + node.filebase + '.hh"')
            self.sci.out('#ifdef MODULE_CONTAINS_' + self.masterGuard)
            self.sci.out('#define PUBLIC_' + self.masterGuard + '_PRE CDA_EXPORT_PRE')
            self.sci.out('#define PUBLIC_' + self.masterGuard + '_POST CDA_EXPORT_POST')
            self.sci.out('#else')
            self.sci.out('#define PUBLIC_' + self.masterGuard + '_PRE CDA_IMPORT_PRE')
            self.sci.out('#define PUBLIC_' + self.masterGuard + '_POST CDA_IMPORT_POST')
            self.sci.out('#endif')
        for n in node.declarations():
            if n.file() == self.masterFile:
                n.accept(self)
            elif self.doing_header:
                self.considerIncluding(n.file())
        if self.doing_header:
            self.escapeScopes()
            self.sci.out('#undef PUBLIC_' + self.masterGuard + '_PRE')
	    self.sci.out('#undef PUBLIC_' + self.masterGuard + '_POST')
            self.sci.out('#endif // _SCI' + self.masterGuard + '_hxx')
    
    def escapeScopes(self):
        for i in range(0, self.scopeEntryDepth):
            self.sci.dec_indent()
            self.sci.out('};')
        self.scopeEntryDepth = 0
    
    def writeScopes(self):
        for i in range(self.scopeEntryDepth, len(self.scope)):
            self.sci.out('namespace ' + self.scope[i])
            self.sci.out('{')
            self.sci.inc_indent()
        self.scopeEntryDepth = len(self.scope)
    
    def enterScope(self, node):
        self.scope.append(node.simplename)
    
    def leaveScope(self):
        self.scope = self.scope[:-1]
        if self.scopeEntryDepth > len(self.scope):
            self.scopeEntryDepth = len(self.scope)
            self.sci.dec_indent()
            self.sci.out('};')
    
    def considerIncluding(self, name):
        if (self.beenIncluded.has_key(name)):
            return
        self.beenIncluded[name] = 1;
        self.escapeScopes()
        basename,ext = os.path.splitext(name)
        self.sci.out('#include "SCI' + basename  + '.hxx"')
        self.sci.inModule = 0
    
    def visitModule(self, node):
        """Visit all the definitions in a module."""
        self.enterScope(node)

        for n in node.definitions():
            if n.file() == self.masterFile:
                if self.doing_header:
                    self.writeScopes()
                n.accept(self)
            elif self.doing_header:
                self.considerIncluding(n.file())
        self.leaveScope()

    def processBase(self, active, base):
        # Interface active has base(or active == base). Called only once
        # per active per base. We only care about callables here.
        
        psemi = ''
        pfq = 'SCI::' + active.finalcciscoped + '::'
        if self.doing_header:
            psemi = ';'
            pfq = ''
        
        downcastName = '_downcast_' + string.join(base.scopedName(), '_')
        self.sci.out(base.simplecxxscoped + '* ' + pfq +\
                     downcastName + '()' + psemi)
        if not self.doing_header:
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('return _obj;')
            self.sci.dec_indent()
            self.sci.out('}')

    def writeAddRef(self):
        self.sci.out('{')
        self.sci.inc_indent()
        self.sci.out('_refcount++;')
        self.sci.dec_indent()
        self.sci.out('}')

    def writeReleaseRef(self):
        self.sci.out('{')
        self.sci.inc_indent()
        self.sci.out('_refcount--;')
        self.sci.out('if (_refcount == 0)')
        self.sci.out('{')
        self.sci.inc_indent()
        # Delete this...
        self.sci.out('try')
        self.sci.out('{')
        self.sci.inc_indent()
        # We do not delete yet, we just deactivate, and a delete will follow...
        self.sci.out('::PortableServer::ObjectId_var oid = ' +
                     '_getPOA()->servant_to_id(this);')
        self.sci.out('_getPOA()->deactivate_object(oid);')
        self.sci.dec_indent()
        self.sci.out('}')
        self.sci.out('catch (CORBA::Exception& e)')
        self.sci.out('{')
        self.sci.out('}')
        self.sci.dec_indent()
        self.sci.out('}')
        self.sci.dec_indent()
        self.sci.out('}')

    def writeQueryInterface(self):
        self.sci.out('{')
        self.sci.inc_indent()
        # Write a CORBA query_interface...
        self.sci.out('void* sobj = ' +\
                     '_downcast_XPCOM_IObject()->query_interface(id);')
        # From this point, cobj needs to be release_refd or used...
        # Attempt to wrap it...
        self.sci.out('::XPCOM::IObject_ptr cobj = ' +\
                     'sobj ? gWrapperRepository().NewSCI(id, sobj, _getPOA()) : ' +\
                     '::XPCOM::IObject::_nil();')
        self.sci.out('return cobj;')
        self.sci.dec_indent()
        self.sci.out('}')

    def visitOperation(self, op):
        active = self.active_interface
        downcastStr = '_downcast_' + string.join(active.scopedName(), '_') +\
                      '()'
        psemi = ''
        pfq = 'SCI::' + active.corbacxxscoped + '::'
        if self.doing_header:
            psemi = ';'
            pfq = ''
        # Firstly, get the return type...
        rtype = corbacxx.typeToCORBACXX(op.returnType(),
                                        corbacxx.DIRECTION_RET)
        # Next, build up all the parameters...
        parstr = ''
        callstr = ''
        needcomma = 0
        for p in op.parameters():
            if needcomma:
                parstr = parstr + ', '
            else:
                needcomma = 1
            if p.is_in():
                if p.is_out():
                    direction = corbacxx.DIRECTION_INOUT
                else:
                    direction = corbacxx.DIRECTION_IN
            else:
                direction = corbacxx.DIRECTION_OUT
            parstr = parstr + corbacxx.typeToCORBACXX(p.paramType(), \
                                                      direction) + ' ' +\
                                                      p.simplename
        
        self.sci.out(rtype + ' ' + pfq + op.simplename + '(' + parstr +\
                     ')' + psemi)
        if self.doing_header:
            return
        self.sci.ci_count = 0
        if op.simplename == 'add_ref':
            self.writeAddRef()
        elif op.simplename == 'release_ref':
            self.writeReleaseRef()
        elif op.simplename == 'query_interface':
            self.writeQueryInterface()
        else:
            self.sci.out('{')
            self.sci.inc_indent()
        
            # All in parameters get converted to simple parameters
            for p in op.parameters():
                if callstr != '':
                    callstr = callstr + ','
                if p.is_out():
                    amp = '&'
                else:
                    amp = ''
                if simplecxx.doesTypeNeedLength(p.paramType()):
                    callstr = callstr + amp + '_length_' + p.simplename + ', '
                    self.sci.out('size_t _length_' + p.simplename + ';')
                callstr = callstr + amp + '_simple_' + p.simplename
                self.declareSimpleStorage(p.paramType(), '_simple_' +\
                                          p.simplename)
                # If it isn't an in parameter, leave it for now...
                if not p.is_in():
                    continue
                if simplecxx.doesTypeNeedLength(p.paramType()):
                    sname = '_simple_' + p.simplename
                    slength = '_length_' + p.simplename
                    self.CORBASequenceToSimple(p.paramType(), p.simplename, \
                                               sname, slength, 1, 1)
                else:
                    sname = '_simple_' + p.simplename
                    self.CORBAValueToSimple(p.paramType(), p.simplename, \
                                            sname, 1)
            # Declare storage for the return value...
            rt = op.returnType()
            returns = (rt.kind() != idltype.tk_void)
            retprefix = ''
            if returns:
                if simplecxx.doesTypeNeedLength(rt):
                    retlength = 1
                    self.sci.out('size_t _length_return;');
                    if callstr == '':
                        callstr = callstr + ', '
                    callstr = callstr + '&_length_return'
                else:
                    retlength = 0
                self.declareSimpleStorage(rt, '_simple_return')
                retprefix = '_simple_return = '
            self.sci.out('try')
            self.sci.out('{')
            self.sci.inc_indent()
            # Next, make the call...
            self.sci.out(retprefix + downcastStr + '->' +\
                         op.simplename + '(' + callstr + ');')

            self.sci.dec_indent()
            self.sci.out('}')
            for r in op.raises():
                self.sci.out('catch (::' + r.simplecxxscoped + '& _e)')
                self.sci.out('{')
                self.sci.inc_indent()
                for p in op.parameters():
                    if p.is_in():
                        # Free the CORBA value...
                        if simplecxx.doesTypeNeedLength(p.paramType()):
                            conversionutils.destroySimpleSequence(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename, \
                            '_length_' + p.simplename)
                        else:
                            conversionutils.destroySimpleValue(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename)
                self.sci.out('throw ::' + r.corbacxxscoped + '();')
                self.sci.dec_indent()
                self.sci.out('}')
            self.sci.out('catch (...)')
            self.sci.out('{')
            self.sci.inc_indent()
            for p in op.parameters():
                if p.is_in():
                    # Free the CORBA value...
                    if simplecxx.doesTypeNeedLength(p.paramType()):
                        conversionutils.destroySimpleSequence(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename, \
                            '_length_' + p.simplename)
                    else:
                        conversionutils.destroySimpleValue(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename)
            self.sci.out('throw CORBA::UNKNOWN(/*"A CORBA exception ' +\
                         'occurred."*/);')
            self.sci.dec_indent()
            self.sci.out('}')
            for p in op.parameters():
                if p.is_out():
                    if p.is_in():
                        if simplecxx.doesTypeNeedLength(p.paramType()):
                            conversionutils.destroyCORBASequence(\
                                self.sci, p.paramType(), p.simplename, 1)
                        else:
                            conversionutils.destroyCORBAValue(\
                                self.sci, p.paramType(), p.simplename, 1)
                    # Assign the simple value from the CORBA value.
                    if simplecxx.doesTypeNeedLength(p.paramType()):
                        sname = '_simple_' + p.simplename
                        slength = '_length_' + p.simplename
                        self.simpleSequenceToCORBA(\
                            p.paramType(), sname, slength, p.simplename,\
                            fromCall=p.is_in(), toParam=1)
                    else:
                        sname = '_simple_' + p.simplename
                        self.simpleValueToCORBA(\
                            p.paramType(), sname, p.simplename, toParam=1)
                if p.is_in():
                    # Free the CORBA value...
                    if simplecxx.doesTypeNeedLength(p.paramType()):
                        conversionutils.destroySimpleSequence(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename, \
                            '_length_' + p.simplename)
                    else:
                        conversionutils.destroySimpleValue(\
                            self.sci, \
                            p.paramType(), \
                            '_simple_' + p.simplename)

            if returns:
                self.declareCORBAStorage(rt, '_corba_return')
                if retlength:
                    self.simpleSequenceToCORBA(rt, '_simple_return',\
                                               '_length_return', \
                                               '_corba_return', toParam=1)
                    conversionutils.destroySimpleSequence(\
                        self.sci, rt, '_simple_return', '_length_return')
                else:
                    self.simpleValueToCORBA(rt, '_simple_return', \
                                            '_corba_return', toParam=1)
                    conversionutils.destroySimpleValue(\
                        self.sci, rt, '_simple_return')
                
                self.sci.out('return ' +\
                             conversionutils.returnExpr(rt, '_corba_return') +\
                             ';')            
            self.sci.dec_indent()
            self.sci.out('}')

    def visitAttribute(self, at):
        active = self.active_interface
        downcastStr = '_downcast_' + string.join(active.scopedName(), '_') +\
                      '()'
        psemi = ''
        pfq = 'SCI::' + active.corbacxxscoped + '::'
        if self.doing_header:
            psemi = ';'
            pfq = ''
        typenameIn = corbacxx.typeToCORBACXX(at.attrType(),
                                             corbacxx.DIRECTION_IN)
        typenameRet = corbacxx.typeToCORBACXX(at.attrType(),
                                              corbacxx.DIRECTION_RET)
        self.sci.ci_count = 0        
        for n in at.declarators():
            self.sci.out(typenameRet + ' ' + pfq + n.simplename + '()' + psemi)
            if not self.doing_header:
                self.sci.out('{')
                self.sci.inc_indent()
                self.sci.out('try')
                self.sci.out('{')
                self.sci.inc_indent()
                args = ''
                if simplecxx.doesTypeNeedLength(at.attrType()):
                    self.sci.out('size_t length;')
                    args = '&length'
                self.declareSimpleStorage(at.attrType(), 'value')
                self.sci.out('value = ' + downcastStr + '->' +\
                             n.simplename + '(' + args + ');')
                # Next, convert to a CORBA value...
                self.declareCORBAStorage(at.attrType(), 'corba_value')
                if simplecxx.doesTypeNeedLength(at.attrType()):
                    self.simpleSequenceToCORBA(\
                            at.attrType(), 'value', 'length', 'corba_value',\
                            0, toParam=1)
                    conversionutils.destroySimpleSequence(self.sci, at.attrType(),
                                                          'value', 'length')
                else:
                    self.simpleValueToCORBA(\
                            at.attrType(), 'value', 'corba_value',\
                            0, toParam=1)
                    conversionutils.destroySimpleValue(self.sci, at.attrType(),
                                                       'value')
                self.sci.out('return ' +\
                             conversionutils.returnExpr(at.attrType(),
                                                        'corba_value') + ';')
                self.sci.dec_indent()
                self.sci.out('}')
                self.sci.out('catch (...)')
                self.sci.out('{')
                self.sci.inc_indent()
                self.sci.out('throw CORBA::UNKNOWN();')
                self.sci.dec_indent()
                self.sci.out('}')
                self.sci.dec_indent()
                self.sci.out('}')
            # If its not readonly, we also need a setter...
            if at.readonly():
                return
            self.sci.out('void ' + pfq + n.simplename + '(' + typenameIn +\
                         ' attr)' + psemi)
            if self.doing_header:
                return
            
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('try')
            self.sci.out('{')
            self.sci.inc_indent()
            # Declare storage for the simple value...
            if simplecxx.doesTypeNeedLength(at.attrType()):
                self.sci.out('size_t length;')
            self.declareSimpleStorage(at.attrType(), 'value')
            # Convert the CORBA value to a simple value...
            if simplecxx.doesTypeNeedLength(at.attrType()):
                self.CORBASequenceToSimple(at.attrType(), 'attr', 'value',
                                           'length', 1, 1)
                callstr = 'length, value'
            else:
                self.CORBAValueToSimple(at.attrType(), 'attr', 'value', 1)
                callstr = 'value'
            self.sci.out(downcastStr + '->' + n.simplename + '(' + callstr +\
                         ');')
            if simplecxx.doesTypeNeedLength(at.attrType()):
                conversionutils.destroySimpleSequence(self.sci, at.attrType(),
                                                      'value', 'length')
            else:
                conversionutils.destroySimpleValue(self.sci, at.attrType(),
                                                   'value')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.out('catch (...)')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('throw CORBA::UNKNOWN();')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.dec_indent()
            self.sci.out('}')

    def declareSimpleStorage(self, type, name):
        self.sci.out(simplecxx.typeToSimpleCXX(type) + ' ' + name + ';')

    def declareCORBAStorage(self, type, name):
        # We need to get a storage string...
        self.sci.out(conversionutils.getCORBAVarType(type) + ' ' + name +\
                     ';')

    def simpleSequenceToCORBA(self, type, sarray, slength, cname, fromCall=0,
                              toParam=0):
        conversionutils.writeSimpleSequenceToCORBA(self.sci, type, sarray,
                                                   slength, cname, fromCall,
                                                   toParam)

    def simpleValueToCORBA(self, type, sname, cname, fromCall=0, toParam=0):
        conversionutils.writeSimpleToCORBA(self.sci, type, sname, cname,\
                                           fromCall, toParam)


    def CORBASequenceToSimple(self, type, cname, sarray, slength, fromCall=0,
                              needAlloc=0):
        conversionutils.writeCORBASequenceToSimple(self.sci, type, cname,
                                                   sarray, slength, fromCall,
                                                   needAlloc)
    
    def CORBAValueToSimple(self, type, cname, sname, fromCall=0):
        conversionutils.writeCORBAValueToSimple(self.sci, type, cname, sname, fromCall)

    def writeUnwrap(self, node):
        unwrapName = '_unwrap_' + string.join(node.scopedName(), '_')
        downcastName = '_downcast_' + string.join(node.scopedName(), '_')
	ppre = ''
        psemi = ''
        pfq = 'SCI::' + node.corbacxxscoped + '::'
        if self.doing_header:
	    ppre = 'PUBLIC_' + self.masterGuard + '_PRE'
            psemi =  'PUBLIC_' + self.masterGuard + '_POST;'
            pfq = ''
        self.sci.out(ppre + '::iface::' + node.corbacxxscoped + '* ' + pfq +\
                     unwrapName + '()' + psemi)
        if self.doing_header:
            self.sci.out('virtual ::iface::' + node.corbacxxscoped + '* ' +\
                         downcastName + '() = 0;')
        else:
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('::iface::' + node.corbacxxscoped + '* tmp = ' +\
                         downcastName + '();')
            self.sci.out('if (tmp)')
            self.sci.out('  tmp->add_ref();')
            self.sci.out('return tmp;')
            self.sci.dec_indent()
            self.sci.out('}')

    def writeIObjectSpecials(self):
        # XPCOM::IObject gets some special treatment, since it is the base...
        self.sci.out('public:')
        self.sci.inc_indent()
        self.sci.out('IObject();')
        self.sci.dec_indent()
        self.sci.out('protected:')
        self.sci.inc_indent()
        self.sci.out('::PortableServer::POA_ptr _getPOA();')
        self.sci.out('void _setPOA(::PortableServer::POA_ptr aPOA);')
        self.sci.dec_indent()
        self.sci.out('private:')
        self.sci.inc_indent()
        self.sci.out('::PortableServer::POA_var _poa;')
        self.sci.out('uint32_t _refcount;')
        self.sci.dec_indent()

    def writeIObjectSpecialImpl(self):
        # XPCOM::IObject gets some special treatment, since it is the base...
        self.sci.out('SCI::XPCOM::IObject::IObject() : _refcount(1) {};')
        self.sci.out('void SCI::XPCOM::IObject::_setPOA(::PortableServer::POA_ptr aPOA)')
        self.sci.out('{')
        self.sci.inc_indent()
        self.sci.out('_poa = aPOA;')
        self.sci.dec_indent()
        self.sci.out('}')
        self.sci.out('::PortableServer::POA_ptr SCI::XPCOM::IObject::_getPOA()')
        self.sci.out('{')
        self.sci.inc_indent()
        self.sci.out('return _poa;')
        self.sci.dec_indent()
        self.sci.out('}')

    def visitInterface(self, node):
        isTerminal = 0
        exportFrom = 0
        if self.doing_header:
            # See if this is a terminal interface...
            for p in node.pragmas():
                if p.text() == "terminal-interface":
                    isTerminal = 1
                if p.text() == "cross-module-inheritance" or \
                       p.text() == "cross-module-argument":
                    exportFrom = 1

            #self.sci.out('#ifdef HAVE_VISIBILITY_EXPORT')
            #self.sci.out('extern C {')
            # This is a really ugly hack to export the typeinfo without
            # exporting the whole class on gcc...
            #mangledName = '_ZTIN3SCI' + node.lengthprefixed + 'E'
            #self.sci.out('PUBLIC_' + self.masterGuard + '_PRE void* ' + mangledName +
	    #             'PUBLIC_' + self.masterGuard + '_POST;')
            #self.sci.out('}')
            #self.sci.out('#endif')

	    if exportFrom:
		self.sci.out('PUBLIC_' + self.masterGuard + '_PRE ')
                self.sci.out('class PUBLIC_' + self.masterGuard + '_POST ' +
                             node.simplename)
            else:
                self.sci.out('class ' + node.simplename)

	    inheritstr = node.poacxxscoped
            
            for c in node.inherits():
                isAmbiguous = 0
                target = 'ambiguous-inheritance(' + c.corbacxxscoped + ')'
                for p in node.pragmas():
                    if p.text() == target:
                        isAmbiguous = 1
                        break
                # XPCOM::IObject is automatically ambiguous.
                if c.corbacxxscoped == 'XPCOM::IObject':
                    isAmbiguous = 1
                if isAmbiguous:
                    inheritstr = inheritstr + ' , public virtual SCI::' +\
                                 c.corbacxxscoped
                else:
                    inheritstr = inheritstr + ' , public SCI::' +\
				 c.corbacxxscoped

	    if isTerminal:
		self.sci.out('  : public ' + inheritstr)
	    else:
		self.sci.out('  : public virtual ' + inheritstr)

            self.sci.out('{')
            if (node.corbacxxscoped == 'XPCOM::IObject'):
                self.writeIObjectSpecials()
            self.sci.out('public:')
            self.sci.inc_indent()

            # Also put a trivial virtual destructor...
            self.sci.out('virtual ~' + node.simplename + '(){}')
        else:
            if (node.corbacxxscoped == 'XPCOM::IObject'):
                self.writeIObjectSpecialImpl()

        self.active_interface = node
        self.writeUnwrap(node)
        for c in node.callables():
            c.accept(self)

        if self.doing_header:
            self.sci.dec_indent()
            self.sci.out('};')
            self.sci.out('class _final_' + node.simplename)
            self.sci.out('  : public ' + node.simplename)
            self.sci.out('{')
            self.sci.out('private:')
            self.sci.inc_indent()
            self.sci.out('::iface::' + node.corbacxxscoped + '* _obj;')
            self.sci.dec_indent()
            self.sci.out('public:')
            self.sci.inc_indent()
            self.sci.out('PUBLIC_' + self.masterGuard + '_PRE _final_' +\
			 node.simplename + '(::iface::' + node.corbacxxscoped +\
			 '* _aobj, ' + '::PortableServer::POA_ptr aPp) PUBLIC_' +\
			 self.masterGuard + '_POST;')
            self.sci.out('virtual ~_final_' + node.simplename + '()')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('if (_obj)')
            self.sci.out('  _obj->release_ref();')
            self.sci.dec_indent()
            self.sci.out('}')
            # Servant add & remove ref. Note that these are used by CORBA,
            # which finally results in the release. The standard add_ref and
            # release_ref, on the other hand, are used to decide when to tell
            # CORBA to release.
            self.sci.out('virtual void _add_ref() { _corbarefcount++; }')
            self.sci.out('virtual void _remove_ref()')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('_corbarefcount--;')
            self.sci.out('if (_corbarefcount == 0)')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('delete this;')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.dec_indent()
            self.sci.out('private:')
            self.sci.inc_indent()
            self.sci.out('uint32_t _corbarefcount;')
        else:
            self.sci.out('SCI::' + node.finalcciscoped + '::_final_' +\
                         node.simplename + '(::iface::' +\
                         node.corbacxxscoped + '* _aobj, ' +\
                         '::PortableServer::POA_ptr aPp)')
            self.sci.out(' : _corbarefcount(0)')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('_obj = _aobj;')
            self.sci.out('_obj->add_ref();')
            self.sci.out('_setPOA(::PortableServer::POA::_duplicate(aPp));')
            self.sci.dec_indent()
            self.sci.out('}')
            
        stack = [node]
        seen = {node.simplecxxscoped: 1}
        self.processBase(node, node)
        while len(stack) != 0:
            current = stack.pop()
            for ifa in current.inherits():
                if not seen.has_key(ifa.simplecxxscoped):
                    seen[ifa.simplecxxscoped] = 1
                    while isinstance(ifa, idlast.Declarator):
                        ifa = ifa.alias().aliasType().decl()
                        identifier.AnnotateByRepoID(ifa)
                    stack.append(ifa)
                    self.processBase(node, ifa)

        if self.doing_header:
            self.sci.dec_indent()
            self.sci.out('};')
            self.sci.out('PUBLIC_' + self.masterGuard + '_PRE void prod' +\
			 node.simplename + '() PUBLIC_' + self.masterGuard +\
			 '_POST;')
        else:
            self.writeScopes()
            self.sci.out('class _factory_' + node.simplename)
            self.sci.out('  : public ::SCIFactory')
            self.sci.out('{')
            self.sci.out('public:')
            self.sci.inc_indent()
            self.sci.out('_factory_' + node.simplename + '();')
            self.sci.out('const char* Name() const { return "' +\
                         node.corbacxxscoped + '"; }')
            self.sci.out('::XPCOM::IObject_ptr MakeSCI(void* ' +\
                         'aObj, ::PortableServer::POA_ptr aPp) const')
            self.sci.out('{')
            self.sci.inc_indent()
            # Note: gcc doesn't like dynamic_cast<::*>.
            self.sci.out('::iface::' + node.corbacxxscoped + '* obj = ' +\
                         'reinterpret_cast< ::iface::' + node.corbacxxscoped +\
                         '* >(aObj);')
            self.sci.out('if (obj == NULL) return ::' + node.corbacxxscoped +\
                         '::_nil();')
            self.sci.out('::SCI::' + node.finalcciscoped + ' * x = ' +\
                         'new ::SCI::' + node.finalcciscoped + '(' +\
                         'obj, aPp);')
            self.sci.out('delete aPp->activate_object(x);')
            self.sci.out('obj->release_ref();')
            self.sci.out('return x->_this();')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.dec_indent()
            self.sci.out('};')
            self.escapeScopes()
            self.sci.out('::SCI::' + node.factoryscoped + '::_factory_' +\
                         node.simplename + '()')
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('gWrapperRepository().RegisterSCIFactory(this);')
            self.sci.dec_indent()
            self.sci.out('}')
            self.sci.out('::SCI::' + node.factoryscoped + ' gSCIFactory' +\
                         node.simplecscoped + ';')
            self.writeScopes()
            self.sci.out('void prod' + node.simplename + '() {'+\
                         ' gSCIFactory' + node.simplecscoped + '.Name(); }')
            self.escapeScopes()
    
    def processBase(self, active, base):
        # Interface active has base(or active == base). Called only once
        # per active per base. We only care about callables here.
        
        psemi = ''
        pfq = 'SCI::' + active.finalcciscoped + '::'
        if self.doing_header:
            psemi = ';'
            pfq = ''
        
        downcastName = '_downcast_' + string.join(base.scopedName(), '_')
        self.sci.out('::iface::' + base.corbacxxscoped + '* ' + pfq +\
                     downcastName + '()' + psemi)
        if not self.doing_header:
            self.sci.out('{')
            self.sci.inc_indent()
            self.sci.out('return _obj;')
            self.sci.dec_indent()
            self.sci.out('}')

def run(tree):
    w = Walker()
    w.sci = output.Stream(open("SCI" + tree.filebase + ".cxx", "w"), 2)
    w.doing_header = 0
    tree.accept(w)
    w.sci = output.Stream(open("SCI" + tree.filebase + ".hxx", "w"), 2)
    w.doing_header = 1
    tree.accept(w)

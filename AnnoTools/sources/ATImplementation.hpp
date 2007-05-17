#ifndef _ATImplementation_hpp
#define _ATImplementation_hpp
#include "cda_compiler_support.h"
#include "Utilities.hxx"
#ifdef HAVE_INTTYPES_H
#include <inttypes.h>
#endif
#include <exception>
#include "IfaceCellML_APISPEC.hxx"
#include "IfaceAnnoTools.hxx"
#include <string>

class CDAStringAnnotationImpl
  : public iface::cellml_services::StringAnnotation
{
public:
  CDA_IMPL_ID
  CDA_IMPL_REFCOUNT
  CDA_IMPL_QI2(cellml_services::StringAnnotation, cellml_api::UserData)

  CDAStringAnnotationImpl(const wchar_t* aValue) throw();

  void value(const wchar_t* aValue) throw(std::exception&);
  wchar_t* value() throw(std::exception&);

private:
  std::wstring mString;
};

class CDAObjectAnnotationImpl
  : public iface::cellml_services::ObjectAnnotation
{
public:
  CDA_IMPL_ID
  CDA_IMPL_REFCOUNT
  CDA_IMPL_QI2(cellml_services::ObjectAnnotation, cellml_api::UserData)

  CDAObjectAnnotationImpl(iface::XPCOM::IObject* aValue) throw();

  void value(iface::XPCOM::IObject* aValue) throw(std::exception&);
  iface::XPCOM::IObject* value() throw(std::exception&);

private:
  ObjRef<iface::XPCOM::IObject> mObject;
};

class CDAAnnotationSetImpl
  : public iface::cellml_services::AnnotationSet
{
public:
  CDA_IMPL_ID
  CDA_IMPL_REFCOUNT
  CDA_IMPL_QI1(cellml_services::AnnotationSet)

  CDAAnnotationSetImpl() throw();
  ~CDAAnnotationSetImpl() throw();

  wchar_t* prefixURI() throw(std::exception&);
  void setStringAnnotation(iface::cellml_api::CellMLElement* aElement,
                           const wchar_t* aKey,
                           const wchar_t* aValue)
     throw(std::exception&);
  wchar_t* getStringAnnotation(iface::cellml_api::CellMLElement* aElement,
                               const wchar_t* aKey)
     throw(std::exception&);
  void setObjectAnnotation(iface::cellml_api::CellMLElement* aElement,
                           const wchar_t* aKey,
                           iface::XPCOM::IObject* aValue)
     throw(std::exception&);
  iface::XPCOM::IObject* getObjectAnnotation(iface::cellml_api::CellMLElement* aElement,
                                             const wchar_t* aKey)
     throw(std::exception&);
private:
  std::wstring mPrefixURI;
  std::list<std::pair<std::wstring, iface::cellml_api::CellMLElement*> >
    mAnnotations;
};

class CDAAnnotationToolServiceImpl
  : public iface::cellml_services::AnnotationToolService
{
public:
  CDA_IMPL_ID
  CDA_IMPL_REFCOUNT
  CDA_IMPL_QI1(cellml_services::AnnotationToolService)

  CDAAnnotationToolServiceImpl() throw()
    : _cda_refcount(1)
  {
  }

  iface::cellml_services::AnnotationSet* createAnnotationSet()
    throw(std::exception&)
  {
    return new CDAAnnotationSetImpl();
  }
};

#endif // _ATImplementation_hpp
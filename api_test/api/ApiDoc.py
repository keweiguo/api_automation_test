import json
import logging
import re

import time
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view

from api_test.common import GlobalStatusCode
from api_test.common.WriteDocx import Write
from api_test.common.api_response import JsonResponse
from api_test.common.common import verify_parameter, record_dynamic
from api_test.models import Project, ApiGroupLevelFirst, ApiGroupLevelSecond, ApiInfo, \
    ApiOperationHistory, APIRequestHistory, ApiHead, ApiParameter, ApiResponse, ApiParameterRaw
from api_test.serializers import ApiGroupLevelFirstSerializer, ApiInfoSerializer, APIRequestHistorySerializer, \
    ApiOperationHistorySerializer, ApiInfoListSerializer, ApiInfoDocSerializer

logger = logging.getLogger(__name__)  # 这里使用 __name__ 动态搜索定义的 logger 配置，这里有一个层次关系的知识点。


@api_view(["GET"])
@verify_parameter(["project_id", ], "GET")
def group(request):
    """
    接口分组
    project_id 项目ID
    :return:
    """
    project_id = request.GET.get("project_id")
    if not project_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())

    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiGroupLevelFirst.objects.filter(project=project_id).order_by("id")
        serialize = ApiGroupLevelFirstSerializer(obi, many=True)
        return JsonResponse(data=serialize.data, code_msg=GlobalStatusCode.success())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "name"], "POST")
def add_group(request):
    """
    添加接口分组
    project_id 项目ID
    name  名称
    first_group_id 一级分组ID
    :return:
    """
    project_id = request.POST.get("project_id")
    name = request.POST.get("name")
    first_group_id = request.POST.get("first_group_id")
    if not project_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())

    obj = Project.objects.filter(id=project_id)
    if obj:
        # 添加二级分组名称
        if first_group_id:
            if not first_group_id.isdecimal():
                return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
            obi = ApiGroupLevelFirst.objects.filter(id=first_group_id, project=project_id)
            if obi:
                obi = ApiGroupLevelSecond(apiGroupLevelFirst=
                                          ApiGroupLevelFirst.objects.get(id=first_group_id), name=name)
                obi.save()
            else:
                return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
        # 添加一级分组名称
        else:
            obi = ApiGroupLevelFirst(project=Project.objects.get(id=project_id), name=name)
            obi.save()
        record_dynamic(project_id, "新增", "接口分组", "新增接口分组“%s”" % obi.name)
        return JsonResponse(data={
            "group_id": obi.pk
        }, code_msg=GlobalStatusCode.success())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "name", "first_group_id"], "POST")
def update_name_group(request):
    """
    修改接口分组名称
    project_id 项目ID
    name  名称
    first_group_id 一级分组ID
    second_group_id 二级分组id
    :return:
    """
    project_id = request.POST.get("project_id")
    name = request.POST.get("name")
    first_group_id = request.POST.get("first_group_id")
    second_group_id = request.POST.get("second_group_id")
    if not project_id.isdecimal() or not first_group_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiGroupLevelFirst.objects.filter(id=first_group_id, project=project_id)
        if obi:
            # 修改二级分组名称
            if second_group_id:
                if not second_group_id.isdecimal():
                    return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                obm = ApiGroupLevelSecond.objects.filter(id=second_group_id,
                                                         apiGroupLevelFirst=first_group_id)
                if obm:
                    obm.update(name=name)
                else:
                    return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
            # 修改一级分组名称
            else:
                obi.update(name=name)
            record_dynamic(project_id, "修改", "接口分组", "修改接口分组“%s”" % name)
            return JsonResponse(code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "first_group_id"], "POST")
def del_group(request):
    """
    删除接口分组
    project_id 项目ID
    first_group_id 一级分组id
    second_group_id 二级分组id
    :return:
    """
    project_id = request.POST.get("project_id")
    first_group_id = request.POST.get("first_group_id")
    if not project_id.isdecimal() or not first_group_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    second_group_id = request.POST.get("second_group_id")
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiGroupLevelFirst.objects.filter(id=first_group_id, project=project_id)
        if obi:
            name = obi[0].name
            # 删除二级分组
            if second_group_id:
                if not second_group_id.isdecimal():
                    return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                obi = ApiGroupLevelSecond.objects.filter(id=second_group_id, apiGroupLevelFirst=first_group_id)
                if obi:
                    obi.delete()
                else:
                    return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
            else:
                obi.delete()
            record_dynamic(project_id, "删除", "接口分组", "删除接口分组“%s”" % name)
            return JsonResponse(code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["GET"])
@verify_parameter(["project_id"], "GET")
def api_list(request):
    """
    获取接口列表
    project_id 项目ID
    first_group_id 一级分组ID
    second_group_id 二级分组ID
    page_size  每一页条数
    page 页码
    name 接口名称
    :return:
    """
    try:
        page_size = int(request.GET.get("page_size", 20))
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        return JsonResponse(code_msg=GlobalStatusCode.page_not_int())
    project_id = request.GET.get("project_id")
    first_group_id = request.GET.get("first_group_id")
    second_group_id = request.GET.get("second_group_id")
    name = request.GET.get("name")
    if not project_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        if first_group_id and second_group_id:
            if not first_group_id.isdecimal() or not second_group_id.isdecimal():
                return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
            if name:
                obi = ApiInfo.objects.filter(project=project_id, name__contains=name, apiGroupLevelFirst=first_group_id,
                                             apiGroupLevelSecond=second_group_id).order_by("id")
            else:
                obi = ApiInfo.objects.filter(project=project_id, apiGroupLevelFirst=first_group_id,
                                             apiGroupLevelSecond=second_group_id).order_by("id")
        else:
            if name:
                obi = ApiInfo.objects.filter(project=project_id, name__contains=name).order_by("id")
            else:
                obi = ApiInfo.objects.filter(project=project_id).order_by("id")
        paginator = Paginator(obi, page_size)  # paginator对象
        total = paginator.num_pages  # 总页数
        try:
            obm = paginator.page(page)
        except PageNotAnInteger:
            obm = paginator.page(1)
        except EmptyPage:
            obm = paginator.page(paginator.num_pages)
        serialize = ApiInfoListSerializer(obm, many=True)
        return JsonResponse(data={"data": serialize.data,
                                  "page": page,
                                  "total": total
                                  }, code_msg=GlobalStatusCode.success())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
# @verify_parameter(["project_id", "first_group_id", "name", "httpType", "requestType", "address",
#                    "requestParameterType", "status"], "POST")
def add_api(request):
    """
    新增接口信息
    project_id 项目ID
    first_group_id 一级分组ID
    second_group_id 二级分组ID
    name 接口名称
    httpType  HTTP/HTTPS
    requestType 请求方式
    address  请求地址
    headDict 头文件
    requestParameterType 参数请求格式
    requestList 请求参数列表
    responseList 返回参数列表
    mockStatus  mockhttp状态
    code mock代码
    description 描述
    :return:
    """
    data = json.loads(request.body)
    if not data["project_id"] or not data["first_group_id"] or not data["name"] or not data["httpType"] or not \
            data["requestType"] or not data["address"] or not data["requestParameterType"] or not data["status"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["status"] not in ["True", "False"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if not isinstance(data["project_id"], int) or not isinstance(data["first_group_id"], int):
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["httpType"] not in ["HTTP", "HTTPS"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["requestType"] not in ["POST", "GET", "PUT", "DELETE"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["requestParameterType"] not in ["form-data", "raw", "Restful"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=data["project_id"])
    if obj:
        obi = ApiInfo.objects.filter(name=data["name"], project=data["project_id"])
        if obi:
            return JsonResponse(code_msg=GlobalStatusCode.name_repetition())
        else:
            try:
                with transaction.atomic():
                    first_group = ApiGroupLevelFirst.objects.filter(id=data["first_group_id"], project=data["project_id"])
                    if len(first_group) == 0:
                        return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
                    if data["first_group_id"] and data["second_group_id"]:
                        if not isinstance(data["second_group_id"], int):
                            return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                        second_group = ApiGroupLevelSecond.objects.filter(id=data["second_group_id"],
                                                                          apiGroupLevelFirst=data["first_group_id"])
                        if len(second_group) == 0:
                            return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
                        try:
                            oba = ApiInfo(project=Project.objects.get(id=data["project_id"]),
                                          apiGroupLevelFirst=ApiGroupLevelFirst.objects.get(id=data["first_group_id"]),
                                          apiGroupLevelSecond=ApiGroupLevelSecond.objects.get(id=data["second_group_id"]),
                                          name=data["name"], httpType=data["httpType"], status=data["status"],
                                          requestType=data["requestType"], apiAddress=data["address"],
                                          requestParameterType=data["requestParameterType"],
                                          mockCode=data["mockStatus"], data=data["code"],
                                          userUpdate=User.objects.get(id=request.user.pk), description=data["desc"])
                        except KeyError:
                            return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                    else:
                        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                    oba.save()
                    if len(data["headDict"]):
                        for i in data["headDict"]:
                            try:
                                if i["name"]:
                                    ApiHead(api=ApiInfo.objects.get(id=oba.pk), name=i["name"],
                                            value=i["value"]).save()
                            except KeyError:
                                logging.exception("Error")
                                return JsonResponse(GlobalStatusCode.fail())
                    if data["requestParameterType"] == "form-data":
                        if len(data["requestList"]):
                            for i in data["requestList"]:
                                try:
                                    # i = i.replace("true", "True").replace("false", "False")
                                    if i["name"]:
                                        ApiParameter(api=ApiInfo.objects.get(id=oba.pk), name=i["name"],
                                                     value=i["value"], required=i["required"],
                                                     _type=i["_type"],
                                                     restrict=i["restrict"],
                                                     description=i["description"]).save()
                                except KeyError:
                                    logging.exception("Error")
                                    return JsonResponse(code_msg=GlobalStatusCode.fail())
                    else:
                        if len(data["requestList"]):
                            ApiParameterRaw(api=ApiInfo.objects.get(id=oba.pk), data=data["requestList"]).save()
                    if len(data["responseList"]):
                        for i in data["responseList"]:
                            try:
                                # i = i.replace("true", "True").replace("false", "False")
                                if i["name"]:
                                    ApiResponse(api=ApiInfo.objects.get(id=oba.pk), name=i["name"],
                                                value=i["value"], required=i["required"], _type=i["_type"],
                                                description=i["description"]).save()
                            except KeyError:
                                logging.exception("Error")
                                return JsonResponse(code_msg=GlobalStatusCode.fail())
                    record_dynamic(data["project_id"], "新增", "接口", "新增接口“%s”" % data["name"])
                    api_record = ApiOperationHistory(apiInfo=ApiInfo.objects.get(id=oba.pk), user=User.objects.get(id=request.user.pk),
                                                     description="新增接口\"%s\"" % data["name"])
                    api_record.save()
                    return JsonResponse(data={
                        "api_id": oba.pk
                    }, code_msg=GlobalStatusCode.success())
            except Exception as e:
                logging.exception("error")
                logging.error(e)
                return JsonResponse(code_msg=GlobalStatusCode.fail())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
# @verify_parameter(["project_id", "api_id", "first_group_id", "name", "httpType", "requestType", "address",
#                    "requestParameterType", "status"], "POST")
def update_api(request):
    """
    修改接口信息
    project_id 项目ID
    api_id 接口ID
    first_group_id 一级分组ID
    second_group_id 二级分组ID
    name 接口名称
    httpType  HTTP/HTTPS
    requestType 请求方式
    address  请求地址
    headDict 头文件
    requestParameterType 参数请求格式
    requestList 请求参数列表
    responseList 返回参数列表
    mockStatus  mockhttp状态
    code mock代码
    description 描述
    :return:
    """
    data = json.loads(request.body)
    if not data["project_id"] or not data["first_group_id"] or not data["name"] or not data["httpType"] or not \
            data["requestType"] or not data["address"] or not data["requestParameterType"] or not data["status"] or \
            not data["api_id"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if not isinstance(data["project_id"], int) or not isinstance(data["first_group_id"], int) or \
            not isinstance(data["api_id"], int):
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["status"] not in ["True", "False"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if not isinstance(data["project_id"], int) or not isinstance(data["first_group_id"], int):
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["httpType"] not in ["HTTP", "HTTPS"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["requestType"] not in ["POST", "GET", "PUT", "DELETE"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if data["requestParameterType"] not in ["form-data", "raw", "Restful"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=data["project_id"])
    if obj:
        obm = ApiInfo.objects.filter(id=data["api_id"], project=data["project_id"])
        if obm:
            obi = ApiInfo.objects.filter(name=data["name"], project=data["project_id"]).exclude(id=data["api_id"])
            if len(obi) == 0:
                try:
                    with transaction.atomic():
                        first_group = ApiGroupLevelFirst.objects.filter(id=data["first_group_id"], project=data["project_id"])
                        if len(first_group) == 0:
                            return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
                        if data["first_group_id"] and data["second_group_id"]:
                            if not isinstance(data["second_group_id"], int):
                                return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                            second_group = ApiGroupLevelSecond.objects.filter(id=data["second_group_id"],
                                                                              apiGroupLevelFirst=data["first_group_id"])
                            if len(second_group) == 0:
                                return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
                            try:
                                obm.update(project=Project.objects.get(id=data["project_id"]),
                                           apiGroupLevelFirst=ApiGroupLevelFirst.objects.get(id=data["first_group_id"]),
                                           apiGroupLevelSecond=ApiGroupLevelSecond.objects.get(id=data["second_group_id"]),
                                           name=data["name"], httpType=data["httpType"], requestType=data["requestType"],
                                           apiAddress=data["address"], requestParameterType=data["requestParameterType"],
                                           mockCode=data["mockStatus"], data=data["code"], status=data["status"],
                                           userUpdate=User.objects.get(id=request.user.pk), description=data["description"])
                            except KeyError:
                                return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                        else:
                            return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                        if len(data["headDict"]):
                            _list = []
                            for j in data["headDict"]:
                                try:
                                    _list.append(j["id"])
                                except KeyError:
                                    pass
                            parameter = ApiHead.objects.filter(api=data["api_id"])
                            for n in parameter:
                                if n.pk not in _list:
                                    n.delete()
                            for i in data["headDict"]:
                                if i["name"]:
                                    try:
                                        ApiHead.objects.filter(id=i["id"], api=data["api_id"]).\
                                            update(name=i["name"], value=i["value"])
                                    except KeyError:
                                        ApiHead(api=ApiInfo.objects.get(id=data["api_id"]), name=i["name"],
                                                value=i["value"]).save()
                        if data["requestParameterType"] == "form-data":
                            ApiParameterRaw.objects.filter(api=data["api_id"]).delete()
                            if len(data["requestList"]):
                                _list = []
                                for j in data["requestList"]:
                                    try:
                                        _list.append(j["id"])
                                    except KeyError:
                                        pass
                                parameter = ApiParameter.objects.filter(api=data["api_id"])
                                for n in parameter:
                                    if n.pk not in _list:
                                        n.delete()
                                for i in data["requestList"]:
                                    try:
                                        if i["name"]:
                                            try:
                                                ApiParameter.objects.filter(id=i["id"], api=data["api_id"]).\
                                                    update(name=i["name"], value=i["value"], required=i["required"],
                                                           restrict=i["restrict"], _type=i["_type"],
                                                           description=i["description"])
                                            except KeyError:
                                                ApiParameter(api=ApiInfo.objects.get(id=data["api_id"]), name=i["name"],
                                                             value=i["value"], required=i["required"], _type=i["_type"],
                                                             description=i["description"]).save()
                                    except KeyError:
                                        logging.exception("Error")
                                        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())

                        else:
                            ApiParameterRaw.objects.filter(api=data["api_id"]).delete()
                            ApiParameter.objects.filter(api=data["api_id"]).delete()
                            if data["requestList"]:
                                ApiParameterRaw(api=ApiInfo.objects.get(id=data["api_id"]), data=data["requestList"]).save()

                        if len(data["responseList"]):
                            _list = []
                            for j in data["responseList"]:
                                try:
                                    _list.append(j["id"])
                                except KeyError:
                                    pass
                            parameter = ApiResponse.objects.filter(api=data["api_id"])
                            for n in parameter:
                                if n.pk not in _list:
                                    n.delete()
                            for i in data["responseList"]:
                                if i["name"]:
                                    try:
                                        ApiResponse.objects.filter(id=i["id"], api=data["api_id"]).\
                                            update(name=i["name"], value=i["value"], required=i["required"],
                                                   _type=i["_type"],
                                                   description=i["description"])
                                    except KeyError:
                                        ApiResponse(api=ApiInfo.objects.get(id=data["api_id"]), name=i["name"],
                                                    value=i["value"], required=i["required"], _type=i["_type"],
                                                    description=i["description"]).save()
                            record_dynamic(data["project_id"], "修改", "接口", "修改接口“%s”" % data["name"])
                        api_record = ApiOperationHistory(apiInfo=ApiInfo.objects.get(id=data["api_id"]),
                                                         user=User.objects.get(id=request.user.pk),
                                                         description="修改接口\"%s\"" % data["name"])
                        api_record.save()
                        return JsonResponse(code_msg=GlobalStatusCode.success())
                except Exception as e:
                    logging.exception("ERROR")
                    logging.error(e)
                    return JsonResponse(code_msg=GlobalStatusCode.fail())
            else:
                return JsonResponse(code_msg=GlobalStatusCode.api_is_exist())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "api_ids"], "POST")
def del_api(request):
    """
    删除接口
    project_id  项目ID
    api_ids 接口ID列表
    :return:
    """
    project_id = request.POST.get("project_id")
    if not project_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    ids = request.POST.get("api_ids")
    id_list = ids.split(",")
    for i in id_list:
        if not i.isdecimal():
            return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        for j in id_list:
            obi = ApiInfo.objects.filter(id=j, project=project_id)
            if len(obi) != 0:
                name = obi[0].name
                obi.delete()
                record_dynamic(project_id, "删除", "接口", "删除接口“%s”" % name)
        return JsonResponse(code_msg=GlobalStatusCode.success())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "api_ids", "first_group_id"], "POST")
def update_group(request):
    """
    修改接口所属分组
    project_id  项目ID
    api_ids 接口ID列表
    first_group_id 一级分组ID
    second_group_id 二级分组ID
    :return:
    """
    project_id = request.POST.get("project_id")
    ids = request.POST.get("api_ids")
    id_list = ids.split(",")
    first_group_id = request.POST.get("first_group_id")
    second_group_id = request.POST.get("second_group_id")
    if not project_id.isdecimal() or not first_group_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        api_first_group = ApiGroupLevelFirst.objects.filter(id=first_group_id)
        if api_first_group:
            if first_group_id and second_group_id:
                if not second_group_id.isdecimal():
                    return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                api_second_group = ApiGroupLevelSecond.objects.filter(id=second_group_id)
                if api_second_group:
                    for i in id_list:
                        if not i.isdecimal():
                            return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                    for j in id_list:
                        ApiInfo.objects.filter(id=j, project=project_id).update(
                            apiGroupLevelFirst=ApiGroupLevelFirst.objects.get(id=first_group_id),
                            apiGroupLevelSecond=ApiGroupLevelSecond.objects.get(id=second_group_id))
                else:
                    return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
            elif first_group_id and second_group_id == "":
                for i in id_list:
                    if not i.isdecimal():
                        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
                for j in id_list:
                    ApiInfo.objects.filter(id=j, project=project_id).update(
                        apiGroupLevelFirst=ApiGroupLevelFirst.objects.get(id=first_group_id))
            else:
                return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
            record_dynamic(project_id, "修改", "接口", "修改接口分组，列表“%s”" % id_list)
            return JsonResponse(code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.group_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["GET"])
@verify_parameter(["project_id", "api_id"], "GET")
def api_info(request):
    """
    获取接口详情
    project_id 项目ID
    api_id 接口ID
    :return:
    """
    project_id = request.GET.get("project_id")
    api_id = request.GET.get("api_id")
    if not project_id.isdecimal() or not api_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        try:
            obi = ApiInfo.objects.get(id=api_id, project=project_id)
            serialize = ApiInfoSerializer(obi)
            return JsonResponse(data=serialize.data, code_msg=GlobalStatusCode.success())
        except ObjectDoesNotExist:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "api_id", "requestType", "url", "httpStatus"], "POST")
def add_history(request):
    """
    新增请求记录
    project_id 项目ID
    api_id 接口ID
    requestType 接口请求方式
    url 请求地址
    httpStatus htt状态
    :return:
    """
    project_id = request.POST.get("project_id")
    api_id = request.POST.get("api_id")
    request_type = request.POST.get("requestType")
    url = request.POST.get("url")
    http_status = request.POST.get("httpStatus")
    if not project_id.isdecimal() or not api_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if request_type not in ["POST", "GET", "PUT", "DELETE"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    if http_status not in ["200", "404", "400", "502", "500", "302"]:
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiInfo.objects.filter(id=api_id, project=project_id)
        if obi:
            history = APIRequestHistory(apiInfo=ApiInfo.objects.get(id=api_id, project=project_id),
                                        requestType=request_type, requestAddress=url, httpCode=http_status)
            history.save()
            return JsonResponse(data={
                "history_id": history.pk
            }, code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["GET"])
@verify_parameter(["project_id", "api_id"], "GET")
def history_list(request):
    """
    获取请求历史
    project_id 项目ID
    api_id 接口ID
    :return:
    """
    project_id = request.GET.get("project_id")
    api_id = request.GET.get("api_id")
    if not project_id.isdecimal() or not api_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiInfo.objects.filter(id=api_id, project=project_id)
        if obi:
            history = APIRequestHistory.objects.filter(apiInfo=ApiInfo.objects.get(id=api_id, project=project_id))\
                .order_by("-requestTime")[:10]
            data = APIRequestHistorySerializer(history, many=True).data
            return JsonResponse(data=data, code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["POST"])
@verify_parameter(["project_id", "api_id", "history_id"], "POST")
def del_history(request):
    """
    删除请求历史
    project_id 项目ID
    api_id 接口ID
    history_id 请求历史ID
    :return:
    """
    project_id = request.POST.get("project_id")
    api_id = request.POST.get("api_id")
    history_id = request.POST.get("history_id")
    if not project_id.isdecimal() or not api_id.isdecimal() or not history_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiInfo.objects.filter(id=api_id, project=project_id)
        if obi:
            obm = APIRequestHistory.objects.filter(id=history_id, apiInfo=api_id)
            if obm:
                obm.delete()
                api_record = ApiOperationHistory(apiInfo=ApiInfo.objects.get(id=api_id), user=User.objects.get(id=request.user.pk),
                                                 description="删除请求历史记录")
                api_record.save()
                return JsonResponse(code_msg=GlobalStatusCode.success())
            else:
                return JsonResponse(code_msg=GlobalStatusCode.history_not_exist())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["GET"])
@verify_parameter(["project_id", "api_id"], "GET")
def operation_history(request):
    """
    接口操作历史
    project_id 项目ID
    api_id 接口ID
    page_size 条数
    page 页码
    :return:
    """
    try:
        page_size = int(request.GET.get("page_size", 20))
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        return JsonResponse(code_msg=GlobalStatusCode.page_not_int())
    project_id = request.GET.get("project_id")
    api_id = request.GET.get("api_id")
    if not project_id.isdecimal() or not api_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())
    obj = Project.objects.filter(id=project_id)
    if obj:
        obi = ApiInfo.objects.filter(id=api_id, project=project_id)
        if obi:
            obn = ApiOperationHistory.objects.filter(apiInfo=api_id).order_by("-time")
            paginator = Paginator(obn, page_size)  # paginator对象
            total = paginator.num_pages  # 总页数
            try:
                obm = paginator.page(page)
            except PageNotAnInteger:
                obm = paginator.page(1)
            except EmptyPage:
                obm = paginator.page(paginator.num_pages)
            serialize = ApiOperationHistorySerializer(obm, many=True)
            return JsonResponse(data={"data": serialize.data,
                                      "page": page,
                                      "total": total
                                      }, code_msg=GlobalStatusCode.success())
        else:
            return JsonResponse(code_msg=GlobalStatusCode.api_not_exist())
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


@api_view(["GET"])
@verify_parameter(["project_id"], "GET")
def download(request):
    """
    获取Api下载文档路径
    project_id  项目ID
    :param request:
    :return:
    """
    project_id = request.GET.get("project_id")
    if not project_id.isdecimal():
        return JsonResponse(code_msg=GlobalStatusCode.parameter_wrong())
    obj = Project.objects.filter(id=project_id)
    if obj:
        data = ApiInfoDocSerializer(ApiGroupLevelFirst.objects.filter(project=project_id), many=True).data
        url = Write().write_api(str(obj[0]), data)
        return JsonResponse(code_msg=GlobalStatusCode.success(), data=url)
    else:
        return JsonResponse(code_msg=GlobalStatusCode.project_not_exist())


def download_doc(request):
    url = request.GET.get("url")
    file_name = str(int(time.time()))+".doc"

    def file_iterator(_file, chunk_size=512):
        while True:
            c = _file.read(chunk_size)
            if c:
                yield c
            else:
                break
    _file = open(url, "rb")
    response = StreamingHttpResponse(file_iterator(_file))
    response["Content-Type"] = "application/octet-stream"
    response["Content-Disposition"] = "attachment;filename=\"{0}\"".format(file_name)
    return response

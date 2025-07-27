# ！/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
@Project :  AutoJSEval
@File    :  js_py_test
@Author  :  刘子琦
@Data    :  2025/7/10
@Description: 测试JS代码
    
"""
import json
import subprocess
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
import numpy as np
import yaml
import os
import shutil
import re
import random
import threading
import _thread
from contextlib import contextmanager
DEBUG_MODE = False

def js_constructor(loader, node):
    js_code = loader.construct_scalar(node)
    return {'__js__':js_code}  # 可封装为标记对象，便于后处理

# Add timeout handling context manager
@contextmanager
def timeout(seconds):
    """
    Timeout control context manager

    :param seconds: Timeout duration (seconds)
    """
    timer = threading.Timer(seconds, lambda: _thread.interrupt_main())
    timer.start()
    try:
        yield
    except KeyboardInterrupt:
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    finally:
        timer.cancel()

def test_data_process(function_name,code,test_cases,output_directory,ref_answer_dir,file_stats,type,max_retries=0,timeout_seconds=300):
    for i, test_case in enumerate(test_cases):
        test_case_result = {
            "test_case_id": i + 1,
            "edge_test": test_case.get('edge_test', False),
            "out_type": "",
            "status": "skipped",
            "error": None,
            "retry_count": 0
        }
        print(f"Running test case {i + 1}/{len(test_cases)}...")
        # 测试用例重试机制
        for retry in range(max_retries + 1):
            test_case_result["retry_count"] = retry
            try:
                # Add timeout control
                with timeout(timeout_seconds):
                    params = test_case['params']
                    output_type = test_case['out_type']
                    params_data = params.copy()
                    # params_data = get_params_data(params_data)

                    # 转换成json格式，传给js执行器
                    js_code_json = json.dumps(code)
                    params_json = json.dumps(params_data)
                    if type == 'jsts':
                        result = subprocess.run(
                            ["node", "run_jsts.js", js_code_json, function_name, params_json],
                            capture_output=True, text=True, encoding="utf-8"
                        )
                    else:
                        result = subprocess.run(
                            ["node", "run_function.js", js_code_json, function_name, params_json],
                            capture_output=True, text=True, encoding="utf-8"
                        )
                    error_msg = result.stderr
                    if error_msg:
                        print(f"❌ Test case {i + 1} failed: {error_msg}")
                        test_case_result["error"] = error_msg
                        test_case_result["status"] = "failed"
                        file_stats["failed_test_cases"] += 1
                        break
                    # 转换格式
                    output = json.loads(result.stdout)
                    final_result = output["result"]
                    test_case_result["out_type"] = output_type
                    # 保存结果
                    flag, message = check_result(final_result, test_case, output_directory, output_type,ref_answer_dir)
                if flag:
                    print(f"✅ Test case {i + 1} passed!")
                    test_case_result["status"] = "passed"
                    file_stats["passed_test_cases"] += 1
                    break
                else:
                    message = str(message)
                    print(f"❌ Test case {i + 1} failed: {message}")
                    test_case_result["status"] = "failed"
                    test_case_result["error"] = message
                    file_stats["failed_test_cases"] += 1
                    break
            except TimeoutError as te:
                error_msg = f"Test case timed out after {timeout_seconds} seconds"
                print(f"❌ Test case {i + 1} failed: {error_msg}")
                test_case_result["status"] = "failed"
                test_case_result["error"] = error_msg
                file_stats["failed_test_cases"] += 1
                break
            except Exception as e:
                error_str = str(e)
                if error_str.strip() == "Ok":
                    print(f"✅ Test case {i + 1} passed!")
                    test_case_result["status"] = "passed"
                    file_stats["passed_test_cases"] += 1
                    break
                else:
                    if DEBUG_MODE and output_type == 'error_message':
                        flag, message = check_result(error_str, test_case, output_directory, output_type, ref_answer_dir)
                        if flag:
                            print(f"✅ Test case {i + 1} passed with expected error!")
                            test_case_result["status"] = "passed"
                            file_stats["passed_test_cases"] += 1
                            break
                        else:
                            error_msg = f"Error message mismatch: {error_str}"
                            print(f"❌ Test case {i + 1} failed: {error_msg}")
                            test_case_result["status"] = "failed"
                            test_case_result["error"] = error_msg
                            file_stats["failed_test_cases"] += 1
                            break
                    else:
                        error_msg = f"Unhandled error in test case: {error_str}"

                    print(f"❌ Test case {i + 1} failed: {error_msg}")
                    test_case_result["status"] = "failed"
                    test_case_result["error"] = error_msg
                    file_stats["failed_test_cases"] += 1
                    break
        # If the test case was skipped
        if test_case_result["status"] == "skipped":
            file_stats["skipped_test_cases"] += 1
        # Add test case result to file statistics
        file_stats["test_cases"].append(test_case_result)

    return file_stats

def test_visual(function_name, code, test_cases, output_directory,ref_answer_dir, file_stats,type, max_retries, timeout_seconds):
    for i, test_case in enumerate(test_cases):
        test_case_result = {
            "test_case_id": i + 1,
            "edge_test": test_case.get('edge_test', False),
            "out_type": "",
            "status": "skipped",
            "error": None,
            "retry_count": 0
        }
        print(f"Running test case {i + 1}/{len(test_cases)}...")
        # 测试用例重试机制
        for retry in range(max_retries + 1):
            test_case_result["retry_count"] = retry
            try:
                # Add timeout control
                with timeout(timeout_seconds):
                    params = test_case['params']
                    output_type = test_case['out_type']
                    params_data = params.copy()
                    case_name=test_case['expected_answer'].split('.')[0]
                    pic_path=os.path.join(output_directory, f"pic")
                    eval_method_list=test_case['eval_methods']
                    os.makedirs(pic_path,exist_ok=True)
                    # params_data = get_params_data(params_data)

                    # 转换成json格式，传给js执行器
                    js_code_json = json.dumps(code)
                    params_json = json.dumps(params_data)
                    eval_method_list=json.dumps(eval_method_list)
                    result = subprocess.run(
                        ["node", "run_visual.js", js_code_json, function_name, params_json,case_name,pic_path,type,eval_method_list],
                        capture_output=True, text=True
                    )
                    error_msg=result.stderr
                    if error_msg:
                        print(f"❌ Test case {i + 1} failed: {error_msg}")
                        test_case_result["error"] = error_msg
                        test_case_result["status"] = "failed"
                        file_stats["failed_test_cases"] += 1
                        break
                    #转换格式
                    test_case_result["status"] = "passed"
                    output = json.loads(result.stdout)
                    final_result = output["result"]
                    test_case_result["out_type"] = output_type
                    # 保存结果
                    flag, message = check_visual_result(final_result, test_case, output_directory, output_type, ref_answer_dir)
                    if flag:
                        print(f"✅ Test case {i + 1} passed!")
                        test_case_result["status"] = "passed"
                        file_stats["passed_test_cases"] += 1
                        break
                    else:
                        message = str(message)
                        print(f"❌ Test case {i + 1} failed: {message}")
                        test_case_result["status"] = "failed"
                        test_case_result["error"] = message
                        file_stats["failed_test_cases"] += 1
                        break

            except TimeoutError as te:
                error_msg = f"Test case timed out after {timeout_seconds} seconds"
                print(f"❌ Test case {i + 1} failed: {error_msg}")
                test_case_result["status"] = "failed"
                test_case_result["error"] = error_msg
                file_stats["failed_test_cases"] += 1
                break

            except Exception as e:
                error_str = str(e)
                if error_str.strip() == "Ok":
                    print(f"✅ Test case {i + 1} passed!")
                    test_case_result["status"] = "passed"
                    file_stats["passed_test_cases"] += 1
                    break
                else:
                    if DEBUG_MODE and output_type == 'error_message':
                        flag, message = check_result(error_str, function_name, test_case_result, output_directory,output_type)
                        if flag:
                            print(f"✅ Test case {i + 1} passed with expected error!")
                            test_case_result["status"] = "passed"
                            file_stats["passed_test_cases"] += 1
                            break
                        else:
                            error_msg = f"Error message mismatch: {error_str}"
                            print(f"❌ Test case {i + 1} failed: {error_msg}")
                            test_case_result["status"] = "failed"
                            test_case_result["error"] = error_msg
                            file_stats["failed_test_cases"] += 1
                            break
                    else:
                        error_msg = f"Unhandled error in test case: {error_str}"

                    print(f"❌ Test case {i + 1} failed: {error_msg}")
                    test_case_result["status"] = "failed"
                    test_case_result["error"] = error_msg
                    file_stats["failed_test_cases"] += 1
                    break

        # If the test case was skipped
        if test_case_result["status"] == "skipped":
            file_stats["skipped_test_cases"] += 1
        # Add test case result to file statistics
        file_stats["test_cases"].append(test_case_result)

    return file_stats

def test_single_file(file_path, config, type,output_directory,ref_answer_dir, max_retries=1, retry_delay=60, timeout_seconds=300):
    file_name = os.path.basename(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    file_stats = {
        "file_name": file_name,
        "function_name": None,
        "total_test_cases": 0,
        "passed_test_cases": 0,
        "failed_test_cases": 0,
        "skipped_test_cases": 0,
        "file_errors": [],  # File-level errors
        "test_cases": [],  # Detailed results for each test case
        "status": "skipped"  # Initial status is skipped
    }

    # Matching function names
    function_name_pattern = r"function (\w+)\("  # Match 'function' followed by function name and parenthesis
    function_matches = re.findall(function_name_pattern, code)
    if not function_matches:
        error_msg = "No function definition found in the file"
        file_stats["file_errors"].append(error_msg)
        print(error_msg)
        return file_stats
    function_name = function_matches[0]
    file_stats["function_name"] = function_name

    test_cases = config.get(function_name, [])
    print(f"Testing function: {function_name}")
    if len(test_cases) == 0:
        error_msg = f"No test cases found for {function_name}"
        file_stats["file_errors"].append(error_msg)
        print(print(f"❌ No test cases found for {function_name}"))
        file_stats["status"] = "skipped"
        return file_stats
    file_stats["total_test_cases"] = len(test_cases)

    # Execute each test case

    if type=='leaflet' or type=='openlayers':
        file_stats=test_visual(function_name, code, test_cases, output_directory, ref_answer_dir,file_stats,type, max_retries, timeout_seconds)
    else:
        file_stats = test_data_process(function_name, code, test_cases, output_directory, ref_answer_dir, file_stats, type,max_retries,
              timeout_seconds)


    # Determine the overall status of the file based on test case results
    if file_stats["failed_test_cases"] == 0 and file_stats["passed_test_cases"] > 0:
        file_stats["status"] = "passed"
        print(f"\n✅ All test cases passed for {file_name}")
    elif file_stats["passed_test_cases"] == 0:
        file_stats["status"] = "failed"
        print(f"\n❌ All test cases failed for {file_name}")
    else:
        file_stats["status"] = "partial"  # Some test cases passed
        print(
            f"\n⚠️ {file_stats['passed_test_cases']}/{file_stats['total_test_cases']} test cases passed for {file_name}")

    return file_stats

def check_result(result,test_case, output_directory, output_type,ref_answer_dir):

    expected_answer = test_case['expected_answer']
    answer_path = os.path.join(ref_answer_dir, expected_answer)

    function_case_name = test_case['expected_answer'].split('.')[0]
    result_filename = f"{function_case_name}_output"
    result_path = os.path.join(output_directory, result_filename)

    # ONLY USE IT WHEN DEBUGGING
    if DEBUG_MODE:
        result_path = answer_path

    message = None
    if output_type == "number":
        if not result_path.endswith('.npy'):
            result_path = f"{result_path}.npy"
        if not answer_path.endswith('.npy'):
            answer_path = f"{answer_path}.npy"
        np.save(result_path, np.array(result))

        tolerance = 1e-6
        # Answer check
        answer_number = np.load(answer_path, allow_pickle=True)

        is_close = np.allclose(np.array(result), answer_number, atol=tolerance)
        if is_close:
            flag=True
        else:
            flag = False
    elif output_type == "string":
        if not result_path.endswith('.txt'):
            result_path = f"{result_path}.txt"
        # Save as TXT file
        result_str=str(result)
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(result_str)
        # Answer check
        with open(result_path, encoding='utf-8', mode='r') as f:
            answer_str=f.read()
        if result_str == answer_str:
            flag = True
        else:
            flag = False
    elif output_type == "boolean":
        if not result_path.endswith('.npy'):
            result_path = f"{result_path}.npy"
        if not answer_path.endswith('.npy'):
            answer_path = f"{answer_path}.npy"
        np.save(result_path, np.array(result))

        answer_array = np.load(answer_path, allow_pickle=True)
        is_equal = np.array_equal(answer_array, answer_array)

        if is_equal:
            flag=True
        else:
            flag = False
    elif output_type == "geojson":
        if not result_path.endswith('.geojson'):
            result_path = f"{result_path}.geojson"
        if not answer_path.endswith('.geojson'):
            answer_path = f"{answer_path}.geojson"
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(json.dumps(result))
        # Answer check
        answer_geojson = json.load(open(answer_path))
        answer_geometry = extract_comparable_geometry(answer_geojson)
        result_geometry = extract_comparable_geometry(result)

        if result_geometry:
            return compare_geometry_lists(result_geometry, answer_geometry)
        elif result_geometry==answer_geometry:
            flag = True
        else:
            flag = False
    elif output_type == "Array":
        # Ensure file extension is .npy
        if not result_path.endswith('.npy'):
            result_path = f"{result_path}.npy"
        if not answer_path.endswith('.npy'):
            answer_path = f"{answer_path}.npy"
        result_array=np.array(result)


        np.save(result_path, result_array)
        answer_array = np.load(answer_path, allow_pickle=True)
        try:
            np.testing.assert_array_almost_equal(result_array, answer_array, decimal=3)
            flag = True
        except AssertionError as e:
            flag = False
            message = e
        except Exception as e:
            flag = False
            message = e
    elif output_type == "Object":
        if not result_path.endswith('.json'):
            result_path = f"{result_path}.json"
        if not answer_path.endswith('.json'):
            answer_path = f"{answer_path}.json"
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(json.dumps(result))
        with open(answer_path, encoding='utf-8') as f:
            answer_obj = json.load(f)
        is_equal = compare_result(result, answer_obj)
        if is_equal:
            flag = True
        else:
            flag = False
    elif output_type == "error_message":
        # Ensure file extension is .txt
        if not result_path.endswith('.txt'):
            result_path = f"{result_path}.txt"
        if not answer_path.endswith('.txt'):
            answer_path = f"{answer_path}.txt"
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(str(result))
        with open(answer_path, encoding='utf-8') as f:
            answer_str=f.read()
        if result == answer_str:
            flag = True
        else:
            print(f"Expected: {answer_str}, Got: {result}")
            flag = False
    else:
        print(f"Unsupported output type: {output_type}")
        return False, f"Unsupported output type: {output_type}"
    return flag, "Error when checking: " + str(message)


def check_visual_result(result, test_case, output_directory, output_type, ref_answer_dir):
    expected_answer = test_case['expected_answer']
    answer_path = os.path.join(ref_answer_dir, expected_answer)

    function_case_name = test_case['expected_answer'].split('.')[0]
    result_filename = f"{function_case_name}_output"
    result_path = os.path.join(output_directory, result_filename)

    # ONLY USE IT WHEN DEBUGGING
    if DEBUG_MODE:
        result_path = answer_path

    message = None
    if output_type == "error_message":
        # Ensure file extension is .txt
        if not result_path.endswith('.txt'):
            result_path = f"{result_path}.txt"
        if not answer_path.endswith('.txt'):
            answer_path = f"{answer_path}.txt"
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(str(result))
        with open(answer_path, encoding='utf-8') as f:
            answer_str = f.read()
        if result == answer_str:
            flag = True
        else:
            print(f"Expected: {answer_str}, Got: {result}")
            flag = False
    else:
        if not result_path.endswith('.json'):
            result_path = f"{result_path}.json"
        with open(result_path, encoding='utf-8', mode='w') as f:
            f.write(json.dumps(result))

        with open(answer_path, encoding='utf-8') as f:
            answer_obj = json.load(f)
        flag = compare_result(result, answer_obj)
        if not flag:
            message = f"Result mismatch. Expected: {answer_obj}, Got: {result}"
    return flag, "Error when checking: " + str(message)

def compare_result(result, expected, float_tol=1e-6):
    if isinstance(result, float) and isinstance(expected, float):
        return abs(result - expected) < float_tol

    elif isinstance(result, (int, bool, str)) and isinstance(expected, (int, bool, str)):
        return result == expected

    elif isinstance(result, list) and isinstance(expected, list):
        if len(result) != len(expected):
            return False
        return all(compare_result(r, e, float_tol) for r, e in zip(result, expected))

    elif isinstance(result, dict) and isinstance(expected, dict):
        if result.keys() != expected.keys():
            return False
        return all(compare_result(result[k], expected[k], float_tol) for k in result)

    elif result is None and expected is None:
        return True
    else:
        return False

def run_code_from_txt(code_directory,yaml_path,output_directory,type,reference_directory="./test_code",max_retries=0, retry_delay=60):
    # Register YAML constructor
    yaml.add_constructor('!js', js_constructor)

    files = [f for f in os.listdir(code_directory) if f.endswith('.txt')]

    passed_dir = os.path.join(output_directory, "passed")
    failed_dir = os.path.join(output_directory, "failed")
    output_dir = os.path.join(output_directory, "output_results")
    report_dir = os.path.join(output_directory, "reports")
    ref_dir = os.path.join(reference_directory, f"{type}_code/ref_answer")

    os.makedirs(passed_dir, exist_ok=True)
    os.makedirs(failed_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    if not DEBUG_MODE:
        random.shuffle(files)
    # Read YAML configuration
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.Loader)
    total_files = len(files)

    print(f"Found {total_files} files to test")
    passed_files = 0
    failed_files = 0
    skipped_files = 0
    for file in files:
        file_path = os.path.join(code_directory, file)
        # Test single file
        file_stats = test_single_file(
            file_path,
            config,
            type,
            output_dir,
            ref_dir,
            max_retries,
            retry_delay
        )
        # Move file and update statistics based on test results
        if file_stats["status"] == "passed":
            passed_files += 1
            shutil.move(file_path, os.path.join(passed_dir, file))
        elif file_stats["status"] == "failed" or file_stats["status"] == "partial":
            failed_files += 1
            shutil.move(file_path, os.path.join(failed_dir, file))
        else:
            skipped_files += 1
        # Save test report
        report_path = os.path.join(report_dir, f"{file.replace('.txt', '')}_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(file_stats, f, indent=2, ensure_ascii=False)


def extract_comparable_geometry(geojson_obj):
    """
    从 GeoJSON 中提取可用于比较的 Shapely 几何对象。
    支持 Feature、FeatureCollection 和直接几何结构。
    """
    if not geojson_obj:
        return []

    geo_type = geojson_obj.get("type", "").lower()

    if geo_type == "feature":
        # 单个 Feature：提取 geometry 字段
        geometry = geojson_obj.get("geometry")
        return [shape(geometry)] if geometry else []

    elif geo_type == "featurecollection":
        features = geojson_obj.get("features", [])
        if not features:
            return features
        return [shape(f["geometry"]) for f in features if f.get("geometry")]

    elif geo_type in ["point", "linestring", "polygon", "multipoint", "multilinestring", "multipolygon", "geometrycollection"]:
        # 直接是 geometry：直接解析
        return [shape(geojson_obj)]

    else:
        # 不支持的类型
        return []

def compare_geometry_lists(g1: list[BaseGeometry], g2: list[BaseGeometry], tolerance=1e-6) -> bool:
    """
    比较两个 geometry 列表是否完全一致（顺序无关）。
    """
    if not g1 and not g2:
        return True
    if len(g1) != len(g2):
        return False

        # 将每个 geometry 转为 (sorted_wkt, geometry) 进行排序
    g1_sorted = sorted(g1, key=lambda g: g.wkt)
    g2_sorted = sorted(g2, key=lambda g: g.wkt)

    for geom1, geom2 in zip(g1_sorted, g2_sorted):
        if not geom1.equals_exact(geom2, tolerance):
            return False
    return True


def check_model_result(model_names):
    for model_name in model_names:
        print(f"Starting test for {model_name}...")
        # turf
        # run_code_from_txt(f"./generate_results/{model_name}/turf", r"./test_code/turf_code/config.yaml",
        #                   f"./generate_results/{model_name}/turf_output", "turf", reference_directory="./test_code")
        # leaflet
        run_code_from_txt(f"./generate_results/{model_name}/leaflet", r"./test_code/leaflet_code/config.yaml",
                          f"./generate_results/{model_name}/leaflet_output", "leaflet", reference_directory="./test_code")
        # run_code_from_txt(f"./generate_results/{model_name}/atomic", r"./test_code/atomic_code/atomic_test_config.yaml",
        #                   f"./generate_results/{model_name}/atomic_output", "atomic", reference_directory="./test_code")
        # run_code_from_txt(f"./generate_results/{model_name}/combined", r"./test_code/combined_code/combined_test_config.yaml",
        #                   f"./generate_results/{model_name}/combined_output", "combined", reference_directory="./test_code")
        # run_code_from_txt(f"./generate_results/{model_name}/theme", r"./test_code/theme_code/theme_test_config.yaml",
        #                   f"./generate_results/{model_name}/theme_output", "theme", reference_directory="./test_code")
        print(f"Test for {model_name} completed!\n")


if __name__ == '__main__':

    models=["qwen2.5_1","qwen2.5_2","qwen2.5_3","qwen2.5_4","qwen2.5_5"]

    check_model_result(models)
    print(1)

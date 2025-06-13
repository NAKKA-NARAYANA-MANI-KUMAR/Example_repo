from flask import Flask,jsonify,request, send_file
import json
app=Flask(__name__)


@app.route('/generate_report',methods=['POST'])
def generate_report():
    try:
        data=request.json
    except Exception as e:
        return e
    return data

if __name__=='__main__':
    app.run(debug=True)

